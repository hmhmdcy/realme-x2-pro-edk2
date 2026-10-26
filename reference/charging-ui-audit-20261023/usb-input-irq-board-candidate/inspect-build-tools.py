"""Post-build read-only tool and saved-command binding; no build/guard/device."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/home/cy122/charging-management-20261023/usb-input-irq-board-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
env = {**os.environ, 'PATH': '/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:' + os.environ['PATH']}
result = {'passed': True, 'scope': 'post-build tool versions/hashes and saved commands; no rebuild', 'tools': {}}
for name in ['make', 'aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-ld', 'aarch64-linux-gnu-nm', 'aarch64-linux-gnu-readelf', 'modinfo']:
    path = Path(shutil.which(name, path=env['PATH'])).resolve()
    process = subprocess.run([str(path), '--version'], env=env, capture_output=True)
    assert process.returncode == 0
    result['tools'][name] = {'path': str(path), 'sha256': sha(path),
                             'version_first_line': (process.stdout + process.stderr).decode().splitlines()[0]}
result['tools']['python'] = {'path': str(Path(sys.executable).resolve()), 'sha256': sha(Path(sys.executable).resolve()), 'version': sys.version}
result['saved_commands'] = {str(path.relative_to(PRIVATE)): {'sha256': sha(path), 'first_line': path.read_text().splitlines()[0]}
                            for path in sorted((PRIVATE / 'kbuild/drivers/power/supply').glob('.samurai-usb-input*.cmd'))}
assert result['saved_commands']
result['script_sha256'] = sha(Path(__file__))
(HERE / 'build-tools-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'tool_count': len(result['tools']), 'saved_commands': len(result['saved_commands']),
                  'receipt_sha256': sha(HERE / 'build-tools-result.json')}))
