"""Prepare the reviewed kernel183 bootloader round-trip, without flashing."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import host

parser = argparse.ArgumentParser()
parser.add_argument('--capture', action='store_true')
args = parser.parse_args()
ref = Path(__file__).resolve().parent
old = ref.parent / 'kernel183'
names = ['collect-preflash.py', 'check-quiesce.py', 'disable-crtc.py',
         'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py', 'quiesce-current181.sh']
for name in names:
    text = (old / name).read_text().replace('k183', 'k184').replace('#181 ', '#183 ')
    text = text.replace('current_kernel=181,target_kernel=183', 'current_kernel=183,target_kernel=183')
    text = text.replace('stage=183', 'stage=184').replace("'stage': 183", "'stage': 184")
    text = text.replace('56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55',
                        'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358')
    path = ref / ('quiesce-current183.sh' if name == 'quiesce-current181.sh' else name)
    path.write_text(text)
    if name.endswith('.sh'):
        subprocess.run(['sh', '-n', str(path)], check=True)
print(json.dumps({'prepared': True, 'target_kernel': 183, 'flash_requested': False}))
if not args.capture:
    raise SystemExit(0)
for name in names:
    path = ref / ('quiesce-current183.sh' if name == 'quiesce-current181.sh' else name)
    if name in ['check-quiesce.py', 'disable-crtc.py', 'freeze-for-bootloader.sh']:
        target = '/tmp/k184-' + name
    else:
        target = '/var/lib/samurai/k184-tools/' + path.name
    host.upload(path, target)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + target + '\n').encode())
result = host.ssh('python3 /var/lib/samurai/k184-tools/collect-preflash.py', timeout=55)
(host.PRIVATE / 'pre-reboot-capture-private.log').write_bytes(result.stdout + result.stderr)
print(json.dumps({'current_kernel183_and_partition_hashes_verified': True, 'no_transition_requested': True}))
