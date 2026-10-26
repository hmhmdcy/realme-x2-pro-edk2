from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k264-user/system-6000071');out={}
for name in ['short-stdout-private.json','long-stdout-private.json','short-stderr-private.txt','long-stderr-private.txt','summary.json']:
 p=root/name
 if p.exists():
  s=p.read_text(errors='replace');lines=s.splitlines();out[name]=dict(bytes=p.stat().st_size,tail=lines[-26:],errors=[l for l in lines if any(x in l.lower() for x in ['error','critical','assertion','traceback','segmentation'])][-15:])
print(json.dumps(out))
'''
r=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'system-failure-inspection-private.json').write_bytes(r.stdout)
print(r.stdout.decode())
