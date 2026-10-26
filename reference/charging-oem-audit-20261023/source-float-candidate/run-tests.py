from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
root = Path(__file__).resolve().parent
results = []
for test in ('test-float', 'test-oem'):
    subprocess.run(['cc', '-std=gnu11', '-g', '-O1', '-Wall', '-Wextra', '-Werror',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
        str(root / (test + '.c')), '-o', str(root / test)], check=True)
    out = subprocess.check_output([str(root / test)], text=True)
    results.append(json.loads(out))
with tempfile.TemporaryDirectory(prefix='float-patch-', dir=root) as temp:
    Path(temp, 'samurai-usb-input-decode.h').write_bytes((root / 'original-samurai-usb-input-decode.h').read_bytes())
    subprocess.run(['patch', '--dry-run', '-p1', '-i', str(root / 'float-only.patch')],
                   cwd=temp, capture_output=True, check=True)
result = {'tests': results, 'asan_ubsan': True,
          'patch_dry_run_private_copy': True,
          'header_sha256': hashlib.sha256((root / 'samurai-usb-input-decode.h').read_bytes()).hexdigest(),
          'udc_valid_lifecycle_changed': False, 'phone_accessed': False}
(root / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
