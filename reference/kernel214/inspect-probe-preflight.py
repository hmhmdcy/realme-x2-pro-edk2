from pathlib import Path
import host,json
code=r'''
from pathlib import Path
import json
base=Path('/var/lib/samurai/k214-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
p=Path('/var/lib/samurai/k214-isolated-dark-raw/library-resolution-private.txt')
print(json.dumps(dict(library_resolution=p.read_text() if p.exists() else 'absent',probe_exists=Path('/run/samurai-camera214-probes/raw-dark-sync-probe').exists(),taint=Path('/proc/sys/kernel/tainted').read_text().strip())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);record=json.loads(p.stdout);(host.PRIVATE/'probe-preflight-failure-context-private.json').write_bytes(p.stdout);print(json.dumps(record))
