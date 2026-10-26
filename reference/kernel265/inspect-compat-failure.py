from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k265-user/system-6000091');o={}
for name in ['short','long']:
 p=r/(name+'-stderr-private.txt');s=p.read_text(errors='replace')
 out=r/(name+'-stdout-private.json')
 o[name]=dict(stdout_bytes=out.stat().st_size,stderr_bytes=p.stat().st_size,tail=s.splitlines()[-40:],fatal_lines=[l for l in s.splitlines() if any(k in l.lower() for k in ['segmentation','critical','assertion','aborted','was not recycled','error','traceback'])][-30:])
print(json.dumps(o,indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'compat-6000091-failure-private.json').write_bytes(q.stdout);print(q.stdout.decode())

