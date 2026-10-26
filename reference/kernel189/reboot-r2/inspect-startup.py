import host

code='''from pathlib import Path
import os,json,subprocess
out=Path('/var/lib/samurai/k189r2-startup-inspection');out.mkdir(mode=0o700,exist_ok=True)
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log)
report=dict(taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
 remoteproc={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')},
 power=Path('/sys/devices/platform/sensor-power/state').read_text().strip(),
 runtime_files=[p.name for p in Path('/var/lib/samurai/k189r2-reboot-runtime').iterdir()],
 faults={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',fatal='fatal error received',scm='Assign memory protection call failed',gpu='gpu fault:').items()},
 uname=os.uname().version)
for name in ['samurai-ssc','iio-sensor-proxy']:
 p=subprocess.run(['rc-service',name,'status'],capture_output=True)
 report[name]=dict(exit=p.returncode,output=(p.stdout+p.stderr).decode())
state=Path('/run/samurai-ssc/state.json')
if state.exists():
 d=json.loads(state.read_text());report['ssc_state']={k:d[k] for k in ['started','attempted','stopped'] if k in d}
for name in ['cleanup-error-private.txt','transitions-private.log','accelerometer-readiness-private.log','light-readiness-private.log']:
 p=Path('/run/samurai-ssc')/name
 if p.exists():
  (out/name).write_bytes(p.read_bytes())
  if name in ['cleanup-error-private.txt','transitions-private.log']:report[name]=p.read_text()
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'startup-inspection-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
