from pathlib import Path
import hashlib,json,runpy
ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel75')
report=runpy.run_path(str(ref/'validate-initramfs.py'))
files=report['files']
installed=json.loads((ref/'gpu-installed-manifest.json').read_text())
for name,item in installed.items():
    assert hashlib.sha256(files['lib/firmware/'+name]['body']).hexdigest()==item['sha256']
sha=hashlib.sha256((out/'logdump-k75-diagnostic.img').read_bytes()).hexdigest()
s=(ref.parent/'kernel74/flash-drain.ps1').read_text().replace('k74','k75').replace('kernel74','kernel75').replace('drain-','diagnostic-').replace('logdump-k75-drain.img','logdump-k75-diagnostic.img')
s=s.replace('c7778d45c336b35cf75c2842c083b513343f59a0a1864fe52ad2105d3d55e6c7','8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5')
s=s.replace("$hash -ne '8e43d13658a1d332c441f68a6008e7ebb855177b59fbeb447a196195239f1ee5'","$hash -ne '"+sha+"'")
(ref/'flash-diagnostic.ps1').write_text(s)
print('CPIO includes all three exact stock firmware blobs; diagnostic image SHA '+sha)
