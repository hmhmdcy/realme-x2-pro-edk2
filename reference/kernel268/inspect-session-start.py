"""Read Phosh startup options and the current session launch configuration."""
import json
import host

code=r'''
from pathlib import Path
import json,subprocess,os
desktop=next(p for p in Path('/proc').glob('[0-9]*') if (p/'comm').exists() and (p/'comm').read_text().strip()=='phosh')
q=subprocess.run([os.readlink(desktop/'exe'),'--help'],capture_output=True,text=True,timeout=10)
files={}
for p in [Path('/etc/greetd/config.toml'),Path('/etc/conf.d/greetd'),Path('/usr/bin/phosh-session'),Path('/usr/share/wayland-sessions/phosh.desktop')]:
 if p.is_file():
  try:files[str(p)]=p.read_text()
  except UnicodeDecodeError:files[str(p)]='binary session launcher'
process=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'comm').read_text().strip() in ['phosh','phoc','greetd','user-session']:
   process.append(dict(pid=int(p.name),command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()))
 except OSError:pass
print(json.dumps(dict(help=q.stdout+q.stderr,files=files,process=process)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'session-start-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);print(d['help']);print(json.dumps(d['files'],indent=2));print(json.dumps(d['process']))
