from pathlib import Path
import host, json, hashlib

ref=Path(__file__).resolve().parent
private=host.PRIVATE
names=['quiesce-current183.sh','check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','install-paired-module.py','final-transition.sh']
host.ssh('mkdir -m700 /var/lib/samurai/k200-reboot-tools')
for name in names:
    host.upload(ref/name,'/var/lib/samurai/k200-reboot-tools/'+name)
    if name in ['check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh']:
        host.upload(ref/name,'/tmp/k200-'+name)
module=private.parent/'kernel199/qcom-camss-mmcx-r2.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58'
host.upload(module,'/var/lib/samurai/k200-reboot-tools/qcom-camss-mmcx.ko')
print('K200_PRIVATE_MODULE_AND_GUARDED_TOOLS_UPLOADED_NO_TRANSITION')
