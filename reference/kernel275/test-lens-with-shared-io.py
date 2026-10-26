"""Bounded standard runtime-PM comparison, without changing voltages or lens position."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent;response=host.PRIVATE/'lens-shared-io-r1-response-private.log';assert not response.exists()
code=r'''
from pathlib import Path
import json,os,subprocess,time,traceback
os.umask(0o077);out=Path('/var/lib/samurai/k275-lens-shared-io-r1');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k275-work/boot-id-private.txt').read_bytes()
held=Path('/sys/bus/i2c/devices/7-0010/power/control');original=held.read_text().strip();assert original=='auto'
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='lc898219xi 6-0072')
state=dict(state='preflight',terminal=False,pid=os.getpid());(out/'state-private.json').write_text(json.dumps(state));result={}
try:
 held.write_text('on');assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='active'
 state['state']='wide-held-active';(out/'state-private.json').write_text(json.dumps(state))
 q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls'],capture_output=True,text=True,timeout=10)
 result=dict(held_sensor='imx319 7-0010',main_sensor_still_suspended=Path('/sys/bus/i2c/devices/6-0010/power/runtime_status').read_text().strip()=='suspended',lens_open_exit=q.returncode,controls=q.stdout,stderr=q.stderr,
  cci_kernel_config=[l for l in Path('/boot/config').read_text().splitlines() if 'I2C_QCOM_CCI' in l] if Path('/boot/config').exists() else None)
 (out/'result-private.json').write_text(json.dumps(result))
finally:
 held.write_text(original);time.sleep(3)
 result.update(held_sensor_control_restored=held.read_text().strip()==original,wide_runtime_after=Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip(),lens_runtime_after=Path('/sys/bus/i2c/devices/6-0072/power/runtime_status').read_text().strip())
 state.update(state='terminal',terminal=True);(out/'state-private.json').write_text(json.dumps(state));print(json.dumps(result))
'''
response.write_bytes(b'SUBMISSION INTENT: inspect k275-lens-shared-io-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=25,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout,'Inspect the submitted PM comparison before retrying'
d=json.loads(q.stdout);(R/'lens-shared-io-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
