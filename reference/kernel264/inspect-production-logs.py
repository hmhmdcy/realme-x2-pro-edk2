from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k264-services');out={}
for name in ['pipewire-private.log','wireplumber-private.log']:
 p=root/name;s=p.read_text(errors='replace').splitlines();out[name]=dict(bytes=p.stat().st_size,tail=s[-100:])
print(json.dumps(out))
'''
r=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'production-log-inspection-private.json').write_bytes(r.stdout)
print(r.stdout.decode())
