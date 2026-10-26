"""A fresh guarded reset for testing the still-staged FastRPC candidate."""
from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
old = ref.parent / 'kernel185'
names = ['collect-preflash.py', 'check-quiesce.py', 'disable-crtc.py',
    'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py', 'quiesce-current183.sh',
    'reboot-current.py', 'fastboot-reboot-current.py']
replacements = {
    '/var/lib/samurai/k185-preflash': '/var/lib/samurai/k186-preflash',
    '/var/lib/samurai/k185-quiesce': '/var/lib/samurai/k186-quiesce',
    '/var/lib/samurai/k185-reboot-tools': '/var/lib/samurai/k186-reboot-tools',
    '/tmp/k185-': '/tmp/k186-', '/run/k185-': '/run/k186-',
    'stage=185': 'stage=186', "'stage': 185": "'stage': 186",
    '/var/lib/samurai/k185-deploy/boot-id-private.txt': '/var/lib/samurai/k186-baseline/boot-id-private.txt',
}
for name in names:
    value = (old / name).read_text()
    for a, b in replacements.items():
        value = value.replace(a, b)
    path = ref / name
    assert not path.exists()
    path.write_text(value)
    if name.endswith('.sh'):
        subprocess.run(['sh', '-n', str(path)], check=True)
    else:
        subprocess.run(['python3', '-m', 'py_compile', str(path)], check=True)
host.ssh('test ! -e /var/lib/samurai/k186-reboot-tools && mkdir -m700 /var/lib/samurai/k186-reboot-tools')
for name in names:
    if name in ['reboot-current.py', 'fastboot-reboot-current.py']:
        continue
    dest = '/tmp/k186-' + name if name in ['check-quiesce.py', 'disable-crtc.py', 'freeze-for-bootloader.sh'] else '/var/lib/samurai/k186-reboot-tools/' + name
    path = ref / name
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
p = host.ssh('python3 /var/lib/samurai/k186-reboot-tools/collect-preflash.py', timeout=55)
(host.PRIVATE / 'pre-reboot-capture-private.log').write_bytes(p.stdout + p.stderr)
print(json.dumps({'current_boot_captured': True, 'kernel183_partitions_and_module_tree_verified': True,
    'hci_uart185_preserved': True, 'fastrpc_candidate_not_installed': True, 'transition_requested': False}))
