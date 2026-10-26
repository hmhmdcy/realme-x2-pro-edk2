"""One same-image reset for complete A.11 measurements, not a blind DSP retry."""
from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent
old=ref.parent/'kernel186/reboot-r2'
names=['collect-preflash.py','check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh',
    'linux-restart2-bootloader.py','quiesce-current183.sh','reboot-current.py','fastboot-reboot-current.py']
for name in names:
    value=(old/name).read_text().replace('k186r2','k187')
    value=value.replace('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt','/var/lib/samurai/k186-reboot-runtime-r2/boot-id-private.txt')
    value=value.replace("'r2-","'")
    value=value.replace('stage=186','stage=187').replace("'stage': 186","'stage': 187")
    path=ref/name;assert not path.exists();path.write_text(value)
    if name.endswith('.sh'):subprocess.run(['sh','-n',str(path)],check=True)
    else:subprocess.run(['python3','-m','py_compile',str(path)],check=True)
host.ssh('test ! -e /var/lib/samurai/k187-reboot-tools && mkdir -m700 /var/lib/samurai/k187-reboot-tools')
for name in names:
    if name in ['reboot-current.py','fastboot-reboot-current.py']:continue
    path=ref/name
    dest='/tmp/k187-'+name if name in ['check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh'] else '/var/lib/samurai/k187-reboot-tools/'+name
    host.upload(path,dest)
    host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
p=host.ssh('python3 /var/lib/samurai/k187-reboot-tools/collect-preflash.py',timeout=55)
(host.PRIVATE/'pre-reboot-capture-private.log').write_bytes(p.stdout+p.stderr)
print(json.dumps({'fresh_current_boot_captured':True,'original_modules_and_hci185_verified':True,'no_transition_yet_sent':True}))
