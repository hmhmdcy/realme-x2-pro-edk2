"""One guarded charger notification-link update, with in-place safe fallback."""
from pathlib import Path
import base64
import importlib.util
import json
import shlex

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/ui-update')
old = json.loads((out / 'before-manifest.json').read_text())
new_path = out.parent / 'service/manifest.json'; new = json.loads(new_path.read_text())
build = json.loads((ref / 'integrated-build-result.json').read_text())
module = Path(build['modules']['samurai-mp2650']['path'])
request = {'old_manifest': old, 'new_manifest': new,
           'transaction': 'ui-update-r2',
           'guard': '/var/lib/samurai/k449-adopted/boot-id-private.txt',
           'files': {new['modules']['samurai-mp2650']['target']: base64.b64encode(module.read_bytes()).decode(),
                     '/usr/share/samurai-charging/manifest.json': base64.b64encode(new_path.read_bytes()).decode()}}
with (out / 'update-request-r2.json').open('x') as stream: json.dump({'count': 1}, stream)
spec = importlib.util.spec_from_file_location('window', ref / 'device-window.py')
window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
response = window.host.ssh('python3 -c ' + shlex.quote((ref / 'update-ui-link.py').read_text()),
                           input=json.dumps(request).encode(), timeout=60, check=False)
(out / 'r2-stdout-private.json').write_bytes(response.stdout); (out / 'r2-stderr-private.txt').write_bytes(response.stderr)
if response.returncode: print(response.stderr.decode(errors='replace')); response.check_returncode()
result = json.loads(response.stdout)
(ref / 'ui-link-update-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
