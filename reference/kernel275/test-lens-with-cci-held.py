"""Distinguish a held CCI domain/clocks from the shared I/O rail supplied by a sensor."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent;response=host.PRIVATE/'lens-cci-held-r1-response-private.log';assert not response.exists()
code=r'''
from pathlib import Path
import json,subprocess,time
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k275-work/boot-id-private.txt').read_bytes()
base=Path('/sys/bus/platform/devices/ac4a000.cci');control=base/'power/control';original=control.read_text().strip();assert original=='auto'
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
result={}
try:
 control.write_text('on');assert (base/'power/runtime_status').read_text().strip()=='active';time.sleep(.15)
 assert all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['6-0010','7-0010','8-002d','9-0010'])
 q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls'],capture_output=True,text=True,timeout=10)
 result=dict(stage=275,only_cci_forced_active=True,all_sensors_suspended=True,lens_open_exit=q.returncode,controls=q.stdout,stderr=q.stderr)
finally:
 control.write_text(original);time.sleep(3);result.update(cci_control_restored=control.read_text().strip()==original,cci_runtime_after=(base/'power/runtime_status').read_text().strip(),lens_runtime_after=Path('/sys/bus/i2c/devices/6-0072/power/runtime_status').read_text().strip())
print(json.dumps(result))
'''
response.write_bytes(b'SUBMISSION INTENT: inspect current PM control if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=25,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'lens-cci-held-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
