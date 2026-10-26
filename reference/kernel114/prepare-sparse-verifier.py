from pathlib import Path
source=Path('/mnt/e/edk2-samurai-out/kernel109/verify-sparse.py')
target=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/verify-sparse.py')
assert not target.exists()
text=source.read_text().replace('/home/cy122/pmos-samurai-kernel109','/home/cy122/pmos-samurai-rootfs114').replace('/mnt/e/edk2-samurai-out/kernel109','/mnt/e/edk2-samurai-out/kernel114')
target.write_text(text)
print('ROOTFS114_SPARSE_VERIFIER_PREPARED')
