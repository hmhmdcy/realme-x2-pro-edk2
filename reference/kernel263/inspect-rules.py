from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
paths=[Path('/usr/share/wireplumber/scripts/monitors/libcamera/create-node.lua'),Path('/usr/share/wireplumber/scripts/monitors/libcamera/enumerate-device.lua')]
o={str(p):p.read_text() for p in paths}
for p in Path('/var/lib/samurai/k263-user/isolated-6000003').glob('*-private.log'):o[p.name]=p.read_text(errors='replace')
print(json.dumps(o))
'''
r=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'rules-inputs-private.json').write_bytes(r.stdout)
d=json.loads(r.stdout)
for name,text in d.items():
 if name.endswith('.lua'):print(name+'\n'+text)
 else:print(name+'\n'+'\n'.join(text.splitlines()[-12:]))
