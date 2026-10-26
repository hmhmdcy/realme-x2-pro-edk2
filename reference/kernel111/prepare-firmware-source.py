from pathlib import Path
import hashlib, shutil

base=Path('/home/cy122/edk2-samurai/repo')
stage=Path('/home/cy122/pmos-samurai-kernel111')
target=stage/'edk2'
out=Path('/mnt/e/edk2-samurai-out/kernel111')
blob=Path('Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb')
assert stage.is_dir() and not target.exists()
assert hashlib.sha256((base/blob).read_bytes()).hexdigest()=='2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb'
shutil.copytree(base,target,symlinks=True)
assert (base/blob).read_bytes()==(target/blob).read_bytes()
shutil.copy2(base/'boot-samurai.img',out/'firmware-source-boot-before.img')
print('ISOLATED_EDK2_SOURCE_READY; original unchanged')
