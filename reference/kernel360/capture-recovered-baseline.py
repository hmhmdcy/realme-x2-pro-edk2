"""Short capture with unchanged installed r27/338 after the recovered boot."""
from pathlib import Path
import base64,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
facts=json.loads((P/'recovered-inventory-secret-private.json').read_text());inventory=json.loads((HERE/'recovered-camera-validation.json').read_text());assert inventory['passed']
cameraIds=[re.search(r'\((.*)\)$',line).group(1) for line in inventory['camera_entries']];assert len(cameraIds)==4
code=r'''
from pathlib import Path
import base64,json,re,subprocess,time
expected=EXPECTED
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected
taint=int(Path('/proc/sys/kernel/tainted').read_text());assert taint==0
start=float(Path('/proc/uptime').read_text().split()[0]);rows=[]
for camera in CAMERAS:
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected
 q=subprocess.run(['cam','--camera',camera,'--stream','width=640,height=480,pixelformat=NV12','--capture=4'],capture_output=True,text=True,timeout=30)
 rows.append(dict(camera=camera,exit_code=q.returncode,stdout=q.stdout,stderr=q.stderr))
 if q.returncode:break
devices=['acb3000.camss','ac4a000.cci','ac4b000.cci']
def status():return {name:Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip() for name in devices}
deadline=time.monotonic()+3
while any(s!='suspended' for s in status().values()) and time.monotonic()<deadline:time.sleep(.1)
logs=subprocess.run(['dmesg'],capture_output=True,text=True).stdout
new=[]
for line in logs.splitlines():
 m=re.search(r'\[\s*(\d+\.\d+)\]',line)
 if m and float(m.group(1))>=start:new.append(line)
print(json.dumps(dict(captures=rows,taint_before=taint,taint_after=int(Path('/proc/sys/kernel/tainted').read_text()),camera_runtime=status(),kernel_log_b64=base64.b64encode(('\n'.join(new)+'\n').encode()).decode())))
'''.replace('EXPECTED',repr(facts['boot_id'])).replace('CAMERAS',repr(cameraIds))
q=host.ssh('python3 -',input=code.encode(),timeout=140);observed=json.loads(q.stdout);(P/'recovered-baseline-captures-private.json').write_bytes(q.stdout)
logs=base64.b64decode(observed['kernel_log_b64']);(P/'recovered-baseline-kernel-log-private.txt').write_bytes(logs)
rows=[]
for row in observed['captures']:
    frames=len(re.findall(r'\bseq:\s*\d+',row['stdout']));errorLines=[line for line in row['stdout'].splitlines() if re.search(r'\berror\b',line,re.I)]
    rows.append(dict(camera=row['camera'],exit_code=row['exit_code'],frames=frames,frame_error_lines=len(errorLines),passed=row['exit_code']==0 and frames==4 and not errorLines))
pattern=rb'WARNING:|Oops:|CCI.*error|Stream stop failed|Failed to disable stream on remote pad|Missing SOF tag|arm-smmu.*[Ff]ault|Unhandled context fault'
report=dict(stage=360,installed_framework='99990.7.2-r27',installed_camss_stage=338,requested_format='640x480 NV12',captures=rows,
    taint_before=observed['taint_before'],taint_after=observed['taint_after'],camera_runtime=observed['camera_runtime'],new_relevant_faults=len(re.findall(pattern,logs)),
    r28_candidate_exercised=False,optical_calibration_verified=False,installed_packages_or_kernel_changed=False)
report['passed']=len(rows)==4 and all(r['passed'] for r in rows) and report['taint_before']==report['taint_after']==0 and not report['new_relevant_faults'] and all(s=='suspended' for s in report['camera_runtime'].values())
(HERE/'recovered-baseline-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
