"""Adapt the already audited reboot path to freshly collected boot202 guards."""
from pathlib import Path
import ast

here = Path(__file__).resolve().parent
old = here.parent / 'kernel200'
before = '/var/lib/samurai/k202-before-reboot'

def save(name, source):
    target = here / name
    assert not target.exists()
    if name.endswith('.py'):
        ast.parse(source)
    target.write_text(source)

source = (here.parent / 'kernel189/reboot-r2/quiesce-current183.sh').read_text()
source = source.replace('/var/lib/samurai/k189r2-preflash', before).replace('k189r2', 'k202')
source = source.replace('old132-module-tree.sha256', 'module-tree.sha256')
source = source.replace('for service in bluetooth', '''# GPS is inactive before stopping its watcher; preserve its default runlevel link.
python3 /tmp/k202-stop-gnss-idle.py
for service in bluetooth''')
source = source.replace('echo K183_CURRENT181_PREFLASH_QUIESCE_COMPLETE', 'echo K202_CURRENT183_QUIESCE_COMPLETE')
save('quiesce-current183.sh', source)

for name in ['disable-crtc.py', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py']:
    source = (old / name).read_text().replace('k200-baseline', 'k202-before-reboot').replace('k200', 'k202')
    source = source.replace("== '512'", "== '0'").replace("=='512'", "=='0'").replace('taint=512', 'taint=0')
    source = source.replace("log.count('WARNING:') == 3", "log.count('WARNING:') == 0")
    source = source.replace("prior.count('WARNING:')==3", "prior.count('WARNING:')==0")
    source = source.replace('# Retain the one193 kernel warning and two199 OF property warnings from this boot.', '# This boot has no baseline kernel warnings.')
    source = source.replace('stage=200', 'stage=202').replace("'stage': 200", "'stage': 202")
    source = source.replace('/var/lib/samurai/k202-deploy/paired-module-tree.sha256', before + '/module-tree.sha256')
    if name == 'freeze-for-bootloader.sh':
        source = source.replace('sync\n', 'sha256sum -c "$before/userspace-check.sha256" > /run/k202-userspace-check.txt\nsync\n')
    save(name, source)

source = (here.parent / 'kernel189/reboot-r2/fastboot-reboot-current.py').read_text()
source = source.replace("host.PRIVATE.parents[1]", "host.PRIVATE.parent")
save('fastboot-reboot-current.py', source)
source = (old / 'refresh-usb-endpoint.ps1').read_text().replace('kernel200', 'kernel202').replace('K200_', 'K202_')
save('refresh-usb-endpoint.ps1', source)
print('Prepared stage202 scripts; no device transition requested.')
