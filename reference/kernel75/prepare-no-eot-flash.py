from pathlib import Path
import hashlib, runpy

root=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel75')
runpy.run_path(str(root/'validate-initramfs.py'))
sha=hashlib.sha256((out/'logdump-k75-no-eot.img').read_bytes()).hexdigest()
s=(root/'flash-matched.ps1').read_text().replace('matched','no-eot')
s=s.replace('5b57e3f3362c11a8f37ca8ddef44783eee86145706b67ab427ef2c47c99fe49d',sha)
(root/'flash-no-eot.ps1').write_text(s)
print('Read-only DSC diagnostic candidate:',sha)
