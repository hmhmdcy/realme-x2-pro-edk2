"""Install the validated incremental charger candidate in an owned window."""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
out = private / 'charging-update-r5'
out.mkdir(exist_ok=True)
old = json.loads((private / 'ui-v4-installed/manifest.json').read_text())
new_path = private / 'service/manifest.json'; new = json.loads(new_path.read_text())
build = json.loads((ref / 'integrated-build-result.json').read_text())
assert new['modules']['samurai-mp2650']['sha256'] == build['modules']['samurai-mp2650']['sha256']
for name in ['samurai-usb-input', 'samurai-gauge-protection']:
    assert new['modules'][name] == old['modules'][name]
module = Path(build['modules']['samurai-mp2650']['path'])
assert hashlib.sha256(module.read_bytes()).hexdigest() == new['modules']['samurai-mp2650']['sha256']
assert json.loads((ref.parent / 'charging-session-20261023/integration-test-result.json').read_text())['passed']
request = {'old_manifest': old, 'new_manifest': new,
           'transaction': 'charging-update-r5',
           'guard': '/var/lib/samurai/k449-adopted/boot-id-private.txt',
           'files': {new['modules']['samurai-mp2650']['target']: base64.b64encode(module.read_bytes()).decode(),
                     '/usr/share/samurai-charging/manifest.json': base64.b64encode(new_path.read_bytes()).decode()}}
with (out / 'update-request.json').open('x') as stream: json.dump({'count': 1}, stream)
(out / 'worker.py').write_bytes((ref / 'update-charger.py').read_bytes())
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
q = window.host.ssh('python3 -c ' + shlex.quote((ref / 'update-charger.py').read_text()),
                    input=json.dumps(request).encode(), timeout=60, check=False)
(out / 'stdout-private.json').write_bytes(q.stdout); (out / 'stderr-private.txt').write_bytes(q.stderr)
if q.returncode:
    print(q.stderr.decode(errors='replace')[-2500:]); raise SystemExit(q.returncode)
result = json.loads(q.stdout)
(ref / 'charger-update-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
