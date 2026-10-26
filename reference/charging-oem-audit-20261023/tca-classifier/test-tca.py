"""Offline synthetic decoder/classification checks. No device transport exists."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parent
linux_root = '/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/tca-classifier'
command = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--', 'gcc', '-std=c11', '-g',
           '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
           '-fno-omit-frame-pointer', linux_root + '/test-tca.c',
           '-o', linux_root + '/test-tca']
build = subprocess.run(command, text=True, capture_output=True)
assert build.returncode == 0, build.stdout + build.stderr
result = subprocess.run(['wsl', '-d', 'Ubuntu', '-u', 'root', '--', linux_root + '/test-tca'],
                        text=True, capture_output=True)
assert result.returncode == 0, result.stdout + result.stderr
report = json.loads(result.stdout)
files = (root / 'tca-reference.h', root / 'test-tca.c',
         root.parent.parent / 'charging-management-20261023/gauge-protocol.h',
         Path('E:/edk2-samurai-out/charging-management-20261023/ti-manual-private.txt'),
         Path('E:/edk2-samurai-out/charging-management-20261023/ti-bq28z610-sluua65.pdf'))
report.update({'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
               'command': command, 'sanitizers': ['ASan', 'UBSan'], 'stderr': result.stderr,
               'phone_accessed': False, 'main_whitelist_modified': False,
               'scope': 'Synthetic saved-packet framing and proposed gated classification only; factory 2719 new commands not validated'})
(root / 'test-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
