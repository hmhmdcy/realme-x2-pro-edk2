"""Apply the candidate to an audit-owned copy only and verify exact output."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
directory = ROOT / 'patch-check'
directory.mkdir(exist_ok=True)
target = directory / 'samurai-mp2650.c'
target.write_text((ROOT / 'before-notification-samurai-mp2650.c').read_text(), newline='\n')
new_header = directory / 'charging-notify.h'
if new_header.exists():
    new_header.unlink()
patch = ROOT / 'notification-state.patch'
subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', str(patch)], cwd=directory, check=True)
subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', str(patch)], cwd=directory, check=True)
assert target.read_bytes() == (ROOT / 'candidate/samurai-mp2650.c').read_bytes()
assert new_header.read_bytes() == (ROOT / 'candidate/charging-notify.h').read_bytes()
result = {'passed': True, 'scope': 'patch applied to audit-owned base copy only',
          'patch_sha256': hashlib.sha256(patch.read_bytes()).hexdigest(),
          'generated_candidate_exact': True, 'production_modified': False}
(ROOT / 'notification-patch-test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
