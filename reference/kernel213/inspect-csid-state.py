import host,json
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='msm_csid0'];assert len(nodes)==1
p=subprocess.run(['v4l2-ctl','-d','/dev/'+nodes[0].name,'--get-ctrl=test_pattern'],capture_output=True,text=True,timeout=10)
print(json.dumps(dict(csid_control_stdout=p.stdout,exit=p.returncode,taint=Path('/proc/sys/kernel/tainted').read_text().strip(),attempt_dir_exists=(root/'k213-helper-raw-csid-p4').exists(),attempt_files=[p.name for p in (root/'k213-helper-raw-csid-p4').iterdir()])))
'''
p=host.ssh('python3 -',input=code.encode());print(p.stdout.decode())
