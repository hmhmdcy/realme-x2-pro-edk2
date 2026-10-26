from pathlib import Path
import json,shlex
import host
code=r'''
from pathlib import Path
import json,subprocess
out=dict(uptime=Path('/proc/uptime').read_text().split()[0],services={})
for name in ['greetd','samurai-ssc','modemmanager','networkmanager','iio-sensor-proxy']:
 q=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True);out['services'][name]=dict(exit=q.returncode,text=q.stdout+q.stderr)
rows=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if any(n in name.lower() for n in ['greet','phoc','phosh','pipewire','wireplumber','dbus','samurai','modem']):rows.append(dict(pid=p.name,uid=p.stat().st_uid,name=name,args=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')))
 except OSError:pass
out['processes']=json.dumps(rows)
out['log_files']=[str(p) for p in Path('/var/log').iterdir()]
out['greetd_config']={str(p):p.read_text() for p in [Path('/etc/greetd/config.toml'),Path('/etc/conf.d/greetd'),Path('/etc/init.d/greetd')] if p.exists()}
for name in ['/var/log/greetd.log','/var/log/messages']:
 p=Path(name)
 if p.exists():out[name]=p.read_text(errors='replace')[-18000:]
print(json.dumps(out))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(host.PRIVATE/'services-observation-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(uptime=d['uptime'],services=d['services'],processes=json.loads(d['processes']),log_files=d['log_files'],greetd_config=d['greetd_config']),indent=2))
