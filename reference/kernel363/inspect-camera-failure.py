from pathlib import Path
import json,shlex
import host
code=r'''
from pathlib import Path
import subprocess,json
media=[]
for p in Path('/sys/class/media').glob('media*'):
 q=subprocess.run(['media-ctl','-d','/dev/'+p.name,'-p'],capture_output=True,text=True)
 media.append(dict(node=p.name,exit=q.returncode,header=q.stdout[:600],stderr=q.stderr[:400]))
p=Path('/var/lib/samurai/k362-install-r1/pipeline-fixture')
print(json.dumps(dict(media=media,fixture_bytes=p.stat().st_size,fixture_mode=oct(p.stat().st_mode),fixture_magic=p.read_bytes()[:20].hex())))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout)
(host.PRIVATE/'camera-failure-inspection-private.json').write_bytes(q.stdout);print(json.dumps(d,indent=2))
