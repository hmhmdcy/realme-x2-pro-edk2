from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
baseline=json.loads((host.PRIVATE.parent/'kernel388/sg-runtime-baseline-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json,subprocess
baseline=BASELINE
for n,row in baseline.items():
 assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['file_sha256']
 assert hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest()==row['note_sha256']
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k378-recovered/boot-id-private.txt').read_bytes()
isp=Path(subprocess.check_output(['modinfo','-n','v4l2_isp'],text=True).strip())
print(json.dumps(dict(kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 original_camss_and_sg_loaded=True,
 static_icp=Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes().rstrip(b'\0').decode(),
 candidate_absent=not any(Path('/sys/module',n).exists() for n in ['camss_icp_a5_m2m','qcom_camss_icp_a5_core','camss_icp_a5_boot_test','v4l2_mem2mem']),
 formal_icp_device_absent=not Path('/sys/bus/platform/devices/ac10000.icp').exists(),
 old_temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 normal_firmware_absent=not Path('/lib/firmware/qcom/sm8150/camera-icp.elf').exists(),
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 existing_isp_sha256=hashlib.sha256(isp.read_bytes()).hexdigest(),
 existing_isp_note_sha256=hashlib.sha256(Path('/sys/module/v4l2_isp/notes/.note.gnu.build-id').read_bytes()).hexdigest())))
'''.replace('BASELINE',repr(baseline))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout)
assert not d['taint'] and d['static_icp']=='disabled' and all(d[k] for k in ['candidate_absent','formal_icp_device_absent','old_temporary_firmware_absent','normal_firmware_absent','original_camss_and_sg_loaded'])
assert all(s=='suspended' for s in d['camera_pm'].values())
report=dict(stage=389,guard378_verified=True,device_mutated_this_stage=False,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
