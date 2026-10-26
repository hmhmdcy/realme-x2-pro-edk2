"""Inspect the completed display restart and greetd's one-shot login marker."""
import json
import host

code=r'''
from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai/k268-unlocked-session');result={}
for name in ['state-private.json','failure-private.txt','stop-greetd-private.log','start-greetd-private.log']:
 p=r/name
 if p.exists():result[name]=p.read_text()[-5000:]
result['config']=Path('/etc/greetd/samurai-phosh.toml').read_text()
result['runfiles']=[dict(path=str(p),is_file=p.is_file(),bytes=p.stat().st_size) for p in Path('/run').glob('*greetd*')]
result['processes']=subprocess.run(['ps','-eo','pid,ppid,comm,args'],capture_output=True,text=True).stdout
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'greetd-transition-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(d['config']);print(json.dumps(d['runfiles']))
for k in ['stop-greetd-private.log','start-greetd-private.log','failure-private.txt']:print(k+': '+d.get(k,''))
print('\n'.join(x for x in d['processes'].splitlines() if any(n in x for n in ['greetd','phosh','phoc','agreety','gnome-session'])))
