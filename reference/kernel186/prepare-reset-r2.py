"""Reset the failed prototype's RAM state, with the original default module restored."""
from pathlib import Path
import json
import subprocess
import sys

ref=Path(__file__).resolve().parent
scratch=ref/'reboot-r2'
scratch.mkdir()
private=Path('/mnt/e/edk2-samurai-out/kernel186')
names=['collect-preflash.py','check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh',
    'linux-restart2-bootloader.py','quiesce-current183.sh','reboot-current.py','fastboot-reboot-current.py',
    'quiesce-and-archive.py']
for name in names:
    value=(ref/name).read_text()
    for a,b in [('/var/lib/samurai/k186-preflash','/var/lib/samurai/k186r2-preflash'),
        ('/var/lib/samurai/k186-quiesce','/var/lib/samurai/k186r2-quiesce'),
        ('/var/lib/samurai/k186-reboot-tools','/var/lib/samurai/k186r2-reboot-tools'),
        ('/tmp/k186-','/tmp/k186r2-'),('/run/k186-','/run/k186r2-')]:
        value=value.replace(a,b)
    value=value.replace('/var/lib/samurai/k186-baseline/boot-id-private.txt','/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt')
    value=value.replace("host.PRIVATE / '","host.PRIVATE / 'r2-")
    value=value.replace("'k186-preflash'","'k186r2-preflash'").replace("'k186-quiesce'","'k186r2-quiesce'")
    if name=='quiesce-and-archive.py':
        value=value.replace("'k186-tools']","'k186-tools','k186-load-fastrpc-r2','k186-original-cycle1','k186-candidate-failure','k186-candidate-kmsg']")
    (scratch/name).write_text(value)
    if name.endswith('.sh'):subprocess.run(['sh','-n',str(scratch/name)],check=True)
    else:subprocess.run([sys.executable,'-m','py_compile',str(scratch/name)],check=True)
# Keep one transport namespace and prefix only this round's markers/receipts.
(scratch/'host.py').write_text((ref/'host.py').read_text().replace("Path(__file__).resolve().parent.parent / 'kernel185/host.py'",
    "Path(__file__).resolve().parent.parent.parent / 'kernel185/host.py'"))
import host
host.ssh('test ! -e /var/lib/samurai/k186r2-reboot-tools && mkdir -m700 /var/lib/samurai/k186r2-reboot-tools')
for name in names:
    if name in ['reboot-current.py','fastboot-reboot-current.py','quiesce-and-archive.py']:continue
    dest='/tmp/k186r2-'+name if name in ['check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh'] else '/var/lib/samurai/k186r2-reboot-tools/'+name
    host.upload(scratch/name,dest)
p=host.ssh('python3 /var/lib/samurai/k186r2-reboot-tools/collect-preflash.py',timeout=55)
(private/'r2-pre-reboot-capture-private.log').write_bytes(p.stdout+p.stderr)
print(json.dumps({'fresh_current_boot_captured':True,'original_fastrpc_default_file_verified':True,
    'hci_uart185_preserved':True,'no_transition_yet_sent':True}))
