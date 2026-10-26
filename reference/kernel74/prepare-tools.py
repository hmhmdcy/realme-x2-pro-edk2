from pathlib import Path
import difflib
import hashlib
import json

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel74')
old=ref.parent/'kernel73'
out=Path('/mnt/e/edk2-samurai-out/kernel74')
kernel=Path('/home/cy122/x2pro-linux/linux')
hash_image=hashlib.sha256((out/'logdump-k74-handoff.img').read_bytes()).hexdigest()
assert hash_image=='25db108b8a19f2d3e1cb695438ee134a1c8e9a04d1db6b57601130aa9cde9e5a'
for name in ('reboot-f1.ps1','reboot-fastboot.ps1','validate-initramfs.py'):
    (ref/name).write_text((old/name).read_text().replace('kernel73','kernel74'))
s=(old/'flash-deps.ps1').read_text().replace('k73','k74').replace('kernel73','kernel74')
s=s.replace("$rollback='E:\\edk2-samurai-out\\kernel74\\logdump-k74-display.img'",
            "$rollback='E:\\edk2-samurai-out\\kernel74\\logdump-before.img'")
s=s.replace('a4435ab347d3e857de88183b6d07969b47306cde1a5370489c95f384935968da',
            'c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7')
s=s.replace('logdump-k74-display-deps.img','logdump-k74-handoff.img')
s=s.replace("$hash -ne 'c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7'",
            "$hash -ne '"+hash_image+"'")
# Replace only evidence names; keep literal fastboot arguments unchanged.
s=s.replace("'deps-", "'handoff-").replace('\\deps-flash-validation.json','\\handoff-flash-validation.json')
assert "@('-s','62bc28a1','reboot')" in s
assert 'logdump-before.img' in s
s=s.replace("$usb=(&",'''$events=Get-Content "$k74out\\handoff-f1-wsl.events.jsonl" | ForEach-Object {$_ | ConvertFrom-Json}
if (!@($events | Where-Object {$_.event -eq 'receipt' -and $_.text -eq 'F1'}).Count) {throw 'No current F1 receipt'}
$usb=(&''',1)
(ref/'flash-handoff.ps1').write_text(s)
patch=[]
for name in ('dpu_kms.c','dpu_rm.c','dpu_rm.h','dpu_hw_ctl.c','dpu_hw_ctl.h'):
    source=kernel/'drivers/gpu/drm/msm/disp/dpu1'/name
    path=str(source.relative_to(kernel))
    patch.extend(difflib.unified_diff((out/(name+'.before')).read_text().splitlines(keepends=True),
        source.read_text().splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path))
(ref/'handoff-candidate.patch').write_text(''.join(patch))
print('Prepared exact-hash, logdump-only deployment and source diff.')
