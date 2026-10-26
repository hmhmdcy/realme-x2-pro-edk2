"""Apply the full R2 patch only to a new private copy of the exact base."""
from pathlib import Path
import hashlib
import json
import subprocess
import uuid

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = HERE.parents[1] / 'charging-oem-audit-20261023/apsd-integration/current-r7/snapshots/drivers--tty--serial--eud.c'
assert sha(base) == '16670a85501bf1bb1d8ae5bd856d991a73ac199028e33275f34f1774991c7bfd'
private = HERE / ('patch-check-' + uuid.uuid4().hex)
target = private / 'drivers/tty/serial'
target.mkdir(parents=True)
(target / 'eud.c').write_bytes(base.read_bytes())
patch = str(HERE / 'eud-window-r2.patch')
for args in [['--check'], []]:
    p = subprocess.run(['git', 'apply', *args, patch], cwd=private,
                       text=True, capture_output=True, timeout=15)
    assert p.returncode == 0, p.stderr
for name in ['eud.c', 'eud-com-window.h']:
    assert (target / name).read_bytes() == (HERE / name).read_bytes()
result = {'passed': True, 'private_directory': private.name,
          'base_sha256': sha(base), 'patch_sha256': sha(HERE / 'eud-window-r2.patch'),
          'candidate_sha256': sha(HERE / 'eud.c'),
          'header_sha256': sha(HERE / 'eud-com-window.h'),
          'exact_bytes_reproduced': True, 'shared_sources_modified': False,
          'phone_ssh_sdk_accessed': False}
(HERE / 'patch-check-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
