from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
for name in state['changed']:assert (source/'drivers/media/platform/qcom/camss'/name).read_bytes()==(host.PRIVATE/(name+'.proposed')).read_bytes()
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 modules=[p.name for p in Path('/sys/module').glob('*icp*')],
 static_icp_status=Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes().rstrip(b'\\0').decode(),
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 temporary_firmware_absent=not any(Path('/lib/firmware/qcom/sm8150',n).exists() for n in ['samurai-icp356.elf','samurai-ipe382-stripe.bin']),
 runtime_payload_names=sorted(json.loads(Path('/var/lib/samurai/k384-boot-r1/manifest.json').read_text())['payload_sha256']))))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and all(v=='suspended' for v in d['camera_pm'].values()) and not d['modules'] and d['static_icp_status']=='disabled' and d['temporary_firmware_absent']
assert len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert not any('stripe' in n or 'iq' in n for n in d['runtime_payload_names'])
runtime=json.loads((HERE/'boot-runtime-validation.json').read_text());assert runtime['passed'] and not runtime['worker_live'] and not runtime['collector_live']
report=dict(stage=384,source_commit=state['commit'],source_clean=True,actual_source_equals_validated_proposal=True,guard378_verified=True,
 latest_hardware_experiment_stage=384,normal_camera_capture_reference_stage=381,camera_capture_repeated=False,
 phone_temporarily_mutated=True,ssc_issue_not_fixed_this_stage=True,candidate_permanently_installed=False,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
