from pathlib import Path
import json, tarfile

root=Path('/mnt/e/RealmeX2Pro edk2/reference');ref=root/'kernel169'
out=Path('/mnt/e/edk2-samurai-out/kernel169');assert not out.exists();out.mkdir(mode=0o700)
files=['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1','enable-transition-eud.ps1']
for name in files:
    text=(root/'kernel168'/name).read_text()
    for a,b in [('kernel168','kernel169'),('k168','k169'),('K168','K169'),('stage=168','stage=169'),('audio168','same168-second')]: text=text.replace(a,b)
    text=text.replace('#163 ','#168 ').replace('CURRENT163','CURRENT168').replace('current_kernel=163','current_kernel=168')
    (ref/name).write_text(text)
with tarfile.open(out/'deployment-tools-private.tar','w') as archive:
    for name in files:
        if not name.endswith('.ps1'): archive.add(ref/name,arcname=name)
print(json.dumps(dict(stage=169,current_kernel=168,target_kernel=168,new_flash=False,fresh_boot_identity_required=True)))
