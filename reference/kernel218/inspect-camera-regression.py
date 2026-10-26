from pathlib import Path
import host,json

code=r'''
from pathlib import Path
import json
p=Path('/var/lib/samurai/k218-candidate-isolated-white-rgb')
print(json.dumps(dict(stderr=(p/'stderr-private.txt').read_text(),stdout=(p/'stdout-private.json').read_text())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'candidate-white-diagnostics-private.json').write_bytes(p.stdout)
data=json.loads(p.stdout)
print('\n'.join(line for line in data['stderr'].splitlines() if any(word in line.lower() for word in ['error','fail','invalid','unsupported','not found','warning'])))
