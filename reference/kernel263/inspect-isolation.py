"""Read the installed daemon/profile interfaces before isolating camera policy."""
from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
files={str(p):p.read_text() for p in [Path('/usr/share/pipewire/pipewire.conf'),Path('/usr/share/wireplumber/wireplumber.conf')]}
profiles={str(p):p.read_text() for p in Path('/usr/share/wireplumber').rglob('*libcamera*') if p.is_file() and p.stat().st_size<100000}
help={n:subprocess.run([n,'--help'],capture_output=True,text=True,timeout=5).stdout for n in ['pipewire','wireplumber']}
print(json.dumps(dict(files=files,libcamera_files=profiles,help=help)))
'''
r=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'daemon-isolation-inputs-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout)
print(json.dumps(dict(help=d['help'],libcamera_files=list(d['libcamera_files']),wireplumber_config_lines=[l for l in d['files']['/usr/share/wireplumber/wireplumber.conf'].splitlines() if any(w in l for w in ['profile','libcamera','monitor.','components'])]),indent=2))
