from pathlib import Path
import ast, json, tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel168')
out=Path('/mnt/e/edk2-samurai-out/kernel168')
files=['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1']
for name in files:
    target=ref/name;assert not target.exists()
    text=(ref.parent/'kernel164'/name).read_text()
    for a,b in [('kernel164','kernel168'),('k164','k168'),('K164','K168'),('stage=164','stage=168'),('firmware164','audio168')]:
        text=text.replace(a,b)
    if name=='check-quiesce.py': text=text.replace('target_kernel=163','target_kernel=168')
    if target.suffix=='.py': ast.parse(text)
    target.write_text(text)
text=(ref.parent/'kernel139/enable-transition-eud.ps1').read_text().replace('kernel139','kernel168').replace('K139','K168').replace('unwind-first','audio168-first')
(ref/'enable-transition-eud.ps1').write_text(text)
with tarfile.open(out/'deployment-tools-private.tar','w') as archive:
    for name in files:
        if not name.endswith('.ps1'): archive.add(ref/name,arcname=name)
print(json.dumps(dict(stage=168,current_kernel=163,target_kernel=168,fresh_device_identity_required=True)))
