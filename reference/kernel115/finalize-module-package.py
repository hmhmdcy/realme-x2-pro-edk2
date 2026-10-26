from pathlib import Path
import shutil,hashlib,json,subprocess,tarfile
stage=Path('/home/cy122/pmos-samurai-kernel115')
pkg=stage/'runtime-package'
out=Path('/mnt/e/edk2-samurai-out/kernel115')
version=(stage/'kernel/include/config/kernel.release').read_text().strip()
assert version=='7.3.0-rc6-rmx1931-samurai+'
modules=pkg/'lib/modules'/version
for name in ['build','source']:
    p=modules/name
    if p.is_symlink(): p.unlink()
firmware=pkg/'lib/firmware/qcom/sm8150/realme/samurai'
firmware.mkdir(parents=True)
for p in (out/'vendor-ipa-source/firmware').iterdir():
    if p.suffix=='.elf': continue
    shutil.copy2(p,firmware/p.name)
assert (firmware/'ipa_fws.mdt').stat().st_size==7020
assert (modules/'kernel/drivers/net/ipa/ipa.ko').is_file()
assert (modules/'kernel/drivers/block/zram/zram.ko').is_file()
subprocess.run(['depmod','-b',str(pkg),version],check=True)
files=[p for p in pkg.rglob('*') if p.is_file()]
(pkg/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(pkg).as_posix()}\n' for p in sorted(files)))
archive=out/'runtime-package-private.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
    tf.add(pkg/'lib',arcname='lib')
    tf.add(pkg/'SHA256SUMS',arcname='SHA256SUMS')
report=dict(kernel_build=115,module_files=len(list(modules.rglob('*.ko'))),archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),full_module_tree=True,depmod_pass=True,own_ipa_firmware=True,goal_complete=False)
(out/'runtime-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
