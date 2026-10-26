from pathlib import Path
import hashlib,host,json

ref=Path(__file__).resolve().parent
names=['quiesce-current183.sh','check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','install-paired-module.py','final-transition.sh']
# Refresh after preparation has reached terminal, then verify the bytes actually staged.
for name in names:
    host.upload(ref/name,'/var/lib/samurai/k200-reboot-tools/'+name)
    if name in ['check-quiesce.py','disable-crtc.py','freeze-for-bootloader.sh']:
        host.upload(ref/name,'/tmp/k200-'+name)
manifest={name:hashlib.sha256((ref/name).read_bytes()).hexdigest() for name in names}
code='from pathlib import Path\nimport hashlib,json\nm='+repr(manifest)+'\nfor n,h in m.items():assert hashlib.sha256((Path("/var/lib/samurai/k200-reboot-tools")/n).read_bytes()).hexdigest()==h,n\nprint("K200_STAGED_TOOLS_BYTE_VERIFIED")\n'
p=host.ssh('python3 -',input=code.encode());print(p.stdout.decode())
