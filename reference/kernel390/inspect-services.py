from pathlib import Path
import json,shlex
import host
code=r'''from pathlib import Path
import json,subprocess
d=dict(uptime=Path('/proc/uptime').read_text().split()[0],services={})
for n in ['samurai-ssc','modemmanager','greetd','networkmanager','iio-sensor-proxy']:
 q=subprocess.run(['rc-service',n,'status'],capture_output=True,text=True,timeout=8);d['services'][n]=dict(exit=q.returncode,text=(q.stdout+q.stderr)[-2000:])
d['remoteprocs']={p.name:dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip()) for p in Path('/sys/class/remoteproc').glob('*')}
d['processes']=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in ['openrc','rc','sscfserv','greetd','phoc','phosh','pipewire','wireplumber','ModemManager','samurai-ssc'] or n.startswith('samurai-'):
   d['processes'].append(dict(pid=int(p.name),name=n,state=(p/'stat').read_text().rsplit(')',1)[1].split()[0]))
 except OSError:pass
d['logs']={}
for name in ['messages','samurai-ssc.log','greetd.log']:
 p=Path('/var/log',name)
 if p.exists():
  with p.open('rb') as f:f.seek(max(0,p.stat().st_size-16000));d['logs'][name]=f.read().decode(errors='replace')
d['greetd_init']=Path('/etc/init.d/greetd').read_text()
print(json.dumps(d))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);d=json.loads(q.stdout);(host.PRIVATE/'services-observation-private.json').write_bytes(q.stdout)
print(json.dumps({k:v for k,v in d.items() if k not in ['logs','greetd_init']},indent=2))
