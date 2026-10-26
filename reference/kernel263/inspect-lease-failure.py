from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k263-user/isolated-6000022')
out={}
for name in ['pipewire-private.log','wireplumber-private.log','survivor-stderr-private.txt']:
 text=(r/name).read_text(errors='replace');lines=text.splitlines()
 out[name]={'tail':lines[-18:],'errors':[l for l in lines if any(x in l.lower() for x in ['error','invalid','-22','-5','failed','busy-ownership'])][-30:]}
print(json.dumps(out))
'''
r=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'lease-failure-inspection-private.json').write_bytes(r.stdout)
print(r.stdout.decode())
