"""Locate the actual required shell component and any existing user override."""
import json
import host

code=r'''
from pathlib import Path
import json,pwd
result={}
for p in [Path('/usr/share/gnome-session/sessions/phosh.session'),*Path('/etc/xdg/autostart').glob('*[Pp]hosh*'),*Path('/usr/share/applications').glob('*[Pp]hosh*'),*Path(pwd.getpwuid(10000).pw_dir,'.config/autostart').glob('*[Pp]hosh*')]:
 if p.is_file():
  try:result[str(p)]=p.read_text()
  except UnicodeDecodeError:pass
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'phosh-desktop-source-private.json').write_bytes(q.stdout);print(q.stdout.decode())
