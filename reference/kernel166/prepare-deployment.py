from pathlib import Path
import ast, json, tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
out=Path('/mnt/e/edk2-samurai-out/kernel166')
files=['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1']
for name in files:
    target=ref/name;assert not target.exists()
    text=(ref.parent/'kernel164'/name).read_text()
    for a,b in [('kernel164','kernel166'),('k164','k166'),('K164','K166'),('stage=164','stage=166'),('firmware164','audio166')]:
        text=text.replace(a,b)
    if name=='check-quiesce.py': text=text.replace('target_kernel=163','target_kernel=166')
    if target.suffix=='.py': ast.parse(text)
    target.write_text(text)
text=(ref.parent/'kernel139/enable-transition-eud.ps1').read_text().replace('kernel139','kernel166').replace('K139','K166').replace('unwind-first','audio166-first')
(ref/'enable-transition-eud.ps1').write_text(text)
with tarfile.open(out/'deployment-tools-private.tar','w') as archive:
    for name in files:
        if not name.endswith('.ps1'): archive.add(ref/name,arcname=name)
print(json.dumps(dict(stage=166,current_kernel=163,target_kernel=166,fresh_device_identity_required=True)))
