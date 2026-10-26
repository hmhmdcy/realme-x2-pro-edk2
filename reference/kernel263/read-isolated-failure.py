import json
import host
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');paths=[r/'k263-pipewire-6000005-r2/stderr-private.txt',r/'k263-user/isolated-6000005/wireplumber-private.log',r/'k263-user/isolated-6000005/probe-stderr-private.txt']
print(json.dumps({str(p):p.read_text(errors='replace')[-5500:] for p in paths if p.exists()}))
'''
r=host.ssh('python3 -',input=code.encode())
(host.PRIVATE/'isolated-candidate-first-failure-private.json').write_bytes(r.stdout)
for name,text in json.loads(r.stdout).items():print(name+'\n'+text)
