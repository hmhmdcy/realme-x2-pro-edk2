from pathlib import Path
import hashlib, json, shutil, tarfile

root=Path('/mnt/e/RealmeX2Pro edk2/reference');ref=root/'kernel167';out=Path('/mnt/e/edk2-samurai-out/kernel167')
assert not out.exists();out.mkdir(mode=0o700)
prior=root/'kernel166'
files=['collect-preflash.py','quiesce-current163.sh','check-quiesce.py','freeze-for-bootloader.sh','enter-bootloader.ps1','enable-transition-eud.ps1']
for name in files:
    text=(prior/name).read_text()
    for a,b in [('kernel166','kernel167'),('k166','k167'),('K166','K167'),('stage=166','stage=167'),('audio166','rollback166')]: text=text.replace(a,b)
    text=text.replace('#163 ','#166 ').replace('CURRENT163','CURRENT166').replace('current_kernel=163','current_kernel=166').replace('target_kernel=166','target_kernel=163')
    text=text.replace("read_text().strip()=='0'","read_text().strip()=='640'").replace('"$(cat /proc/sys/kernel/tainted)" = 0','"$(cat /proc/sys/kernel/tainted)" = 640')
    text=text.replace("prior.count('WARNING:')==0","prior.count('WARNING:')==1").replace("prior.count('WARNING:')==0","prior.count('WARNING:')==1")
    text=text.replace("current.count('WARNING:')==prior.count('WARNING:')==0","current.count('WARNING:')==prior.count('WARNING:')==1")
    text=text.replace('taint=0,current_kernel','taint=640,current_kernel')
    (ref/name).write_text(text)
with tarfile.open(out/'deployment-tools-private.tar','w') as archive:
    for name in files:
        if not name.endswith('.ps1'): archive.add(ref/name,arcname=name)
baseline=json.loads((root/'kernel163/build-package-validation.json').read_text())
image=out/'logdump-rollback163.img';shutil.copyfile(out.parent/'kernel163/logdump-k163-early-reset.img',image)
assert hashlib.sha256(image.read_bytes()).hexdigest()==baseline['logdump_sha256']
(out/'build-package-validation.json').write_text(json.dumps(dict(kernel_build=163,modules132_runtime_compatible=True,dtb_unchanged=True,fat_readback_exact=True,logdump_sha256=baseline['logdump_sha256']),indent=2)+'\n')
text=(prior/'flash-audio.ps1').read_text()
for a,b in [('kernel166','kernel167'),('audio166-first','rollback166-first'),('logdump-k166-audio.img','logdump-rollback163.img'),('kernel_build -ne 166','kernel_build -ne 163'),('K166','K167'),('stage=166','stage=167'),('kernel_build=166','kernel_build=163')]: text=text.replace(a,b)
(ref/'flash-rollback.ps1').write_text(text)
print('K167_ROLLBACK163_VERIFIED_AND_FAILED166_EXIT_TOOLS_PREPARED')
