"""Check the minimal CSR delta against a new private exact R2 copy."""
from pathlib import Path
import hashlib
import json
import subprocess
import uuid

HERE = Path(__file__).resolve().parent
R2 = HERE.parent / 'eud-runtime-window-candidate-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R2 / 'eud.c') == '1479c3cf0be0b4d62a2b66486b3be5819f28da3d380c95ed76c2a1e6966db3af'
assert sha(R2 / 'eud-com-window.h') == '8003aa9619d2f9d1a15d4ff97460b8f106dc54defc841f31670e98d48e2d8c46'
private = HERE / ('patch-check-' + uuid.uuid4().hex)
target = private / 'drivers/tty/serial'
target.mkdir(parents=True)
for name in ['eud.c', 'eud-com-window.h']:
    (target / name).write_bytes((R2 / name).read_bytes())
for args in [['--check'], []]:
    p = subprocess.run(['git', 'apply', *args, str(HERE / 'r2-to-csr.patch')],
                       cwd=private, capture_output=True, text=True, timeout=15)
    assert p.returncode == 0, p.stderr
for name in ['eud.c', 'eud-com-window.h']:
    assert (target / name).read_bytes() == (HERE / name).read_bytes()
text = (HERE / 'eud.c').read_text()
csr = (HERE / 'csr-implementation.inc').read_text().strip()
assert text.count(csr) == 1
assert text.count('int eud_com_csr_begin(') == 1
assert text.count('int eud_com_csr_restore(') == 1
assert 'EUD_REG_CSR_EUD_EN' in csr and 'AHB' not in csr
assert 'eud_restore_ahb2phy' not in csr and 'kernel_restart' not in csr
assert 'EXPORT_SYMBOL' not in text
result = {'passed': True, 'private_directory': private.name,
          'r2_source_sha256': sha(R2 / 'eud.c'),
          'patch_sha256': sha(HERE / 'r2-to-csr.patch'),
          'candidate_sha256': sha(HERE / 'eud.c'),
          'header_sha256': sha(HERE / 'eud-com-window.h'),
          'exact_bytes_reproduced': True, 'no_internal_or_automatic_csr_consumer': True,
          'no_ahb_fifo_or_restart_call_in_csr_stage': True,
          'r2_modified': False, 'phone_ssh_sdk_accessed': False}
(HERE / 'patch-check-result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
