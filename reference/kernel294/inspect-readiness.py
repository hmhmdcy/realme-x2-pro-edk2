from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,subprocess
services={}
for name in ['greetd','samurai-ssc','iio-sensor-proxy','modemmanager','networkmanager','samurai-platform']:
 q=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True);services[name]=dict(exit=q.returncode,output=q.stdout+q.stderr)
procs=subprocess.check_output(['ps','-eo','pid,ppid,comm,stat,etime'],text=True)
dsps={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*')}
report=dict(stage=294,kernel_build=294,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),services=services,remoteprocs=dsps,processes=procs,
 sensor_state=Path('/run/samurai-ssc/state.json').read_text() if Path('/run/samurai-ssc/state.json').exists() else None)
p=Path('/var/lib/samurai/k294-tools/readiness-private.json');p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'readiness-private.json').write_bytes(q.stdout);print(q.stdout.decode())
