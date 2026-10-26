"""Read desktop service ordering and recent session diagnostics."""
from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
code=r'''
from pathlib import Path
import json,subprocess,pwd
result={}
for name in ['/etc/init.d/greetd','/etc/conf.d/greetd','/etc/greetd/config.toml','/etc/greetd/samurai-phosh.toml','/usr/local/bin/samurai-phosh-session','/etc/init.d/samurai-ssc','/usr/share/applications/mobi.phosh.Shell.desktop','/etc/xdg/autostart/mobi.phosh.Shell.desktop']:
 p=Path(name)
 if p.is_file():result[name]=p.read_text()
for p in Path('/var/log').glob('*greet*'):
 if p.is_file():result[str(p)]=p.read_text(errors='replace')[-10000:]
home=Path(pwd.getpwuid(10000).pw_dir)
for name in ['.local/state/samurai-phosh-session.log','.cache/phosh.log','.local/state/phosh.log','.cache/greetd.log','.cache/greetd/session.log','.local/share/greetd/session.log']:
 p=home/name
 if p.is_file():result[str(p)]=p.read_text(errors='replace')[-10000:]
print(json.dumps(result))
'''
q=h.ssh('python3 -',input=code.encode(),timeout=20);(P/'session-startup-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
for n,s in d.items():
 if n.startswith(('/etc/init.d','/etc/conf.d','/usr/local/bin','/usr/share/applications','/etc/xdg')):
  print(n);print(s)
 else:
  print(n+' retained privately')
  if n.endswith('session.log'):
   print('\n'.join(l for l in s.splitlines() if any(x in l.lower() for x in ['sensor-proxy','acceleromet','rotation','net.hadess']))[-5000:])
