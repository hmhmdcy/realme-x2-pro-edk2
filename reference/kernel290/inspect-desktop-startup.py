"""Inspect actual service failures after the planned new boot, without restarting services."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
result={}
for name in ['greetd','samurai-ssc','iio-sensor-proxy','dbus','elogind']:
 p=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True)
 result[name]=dict(exit=p.returncode,text=(p.stdout+p.stderr).strip())
processes={name:subprocess.run(['pgrep','-x',name],capture_output=True,text=True).stdout.split() for name in ['greetd','phoc','phosh','pipewire','wireplumber','iio-sensor-proxy']}
logs={}
for name in ['/var/log/rc.log','/var/log/greetd.log','/var/log/messages','/var/log/samurai-session.log','/tmp/phoc.log']:
 p=Path(name)
 if p.is_file():logs[name]=p.read_text(errors='replace')[-100000:]
private=Path('/var/lib/samurai/k290-startup-diagnostic');assert not private.exists();private.mkdir(mode=0o700)
(private/'logs-private.json').write_text(json.dumps(logs,indent=2)+'\n')
(private/'greetd-service-private.txt').write_bytes(Path('/etc/init.d/greetd').read_bytes())
lines=[]
for name,text in logs.items():
 for line in text.splitlines():
  if any(s in line.lower() for s in ['greetd','samurai-ssc','phoc','phosh','iio-sensor','failed','failure','not found','error']):lines.append(dict(file=name,line=line))
flags={p.name:sorted(x.name for x in p.iterdir()) for p in Path('/run/openrc').glob('*') if p.is_dir() and p.name in ['failed','started','starting','stopping','crashed']}
print(json.dumps(dict(services=result,processes=processes,openrc=flags,logs_found=list(logs),selected_log_lines=lines[-70:],dri={p.name:str(p.resolve()) for p in Path('/dev/dri/by-path').glob('*-card')})))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
r=json.loads(q.stdout);(host.PRIVATE/'desktop-startup-diagnostic-private.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
