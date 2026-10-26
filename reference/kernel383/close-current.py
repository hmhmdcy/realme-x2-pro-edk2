from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
code="""from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 modules=[p.name for p in Path('/sys/module').glob('*icp*')],
 static_icp_status=Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes().rstrip(b'\\0').decode(),
 temporary_firmware_absent=not any(Path('/lib/firmware/qcom/sm8150',n).exists() for n in ['samurai-icp356.elf','samurai-ipe382-stripe.bin']))))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and all(v=='suspended' for v in d['camera_pm'].values()) and not d['modules'] and d['static_icp_status']=='disabled' and d['temporary_firmware_absent']
report=dict(stage=383,source_commit=state['commit'],source_clean=True,guard378_verified=True,
 latest_hardware_experiment_stage=382,normal_camera_capture_reference_stage=381,camera_capture_repeated=False,
 phone_mutated=False,ssc_issue_not_fixed_this_stage=True,candidate_installed=False,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
