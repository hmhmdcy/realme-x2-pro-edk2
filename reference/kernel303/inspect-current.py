"""Read-only current boot and idle camera-resource check."""
from pathlib import Path
import json, shlex
import host
HERE = Path(__file__).resolve().parent
source = (HERE / 'native-capture.py').read_text()
health = source[source.index('def health():'):source.index('\nsave()\ntry:')]
code = 'from pathlib import Path\nimport json,os,re\n' + health + '''
report=dict(stage=303,build=os.uname().version,release=os.uname().release,
 same_298_guard=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes(),
 expected_model=Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\\0',health=health())
print(json.dumps(report))
'''
q = host.ssh('python3 -c '+shlex.quote(code), timeout=20)
report = json.loads(q.stdout)
(HERE / 'current-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
