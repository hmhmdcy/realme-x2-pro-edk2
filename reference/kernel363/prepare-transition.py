"""Prepare a concrete single-transition workflow with current guards and rollback."""
from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'module-staging-validation.json').read_text())['distinct_release_staged']
package=json.loads((HERE/'boot-package-validation.json').read_text());old=json.loads((HERE.parent/'kernel298/boot-package-validation.json').read_text())
adopted=json.loads((P.parent/'kernel360/recovered-boot-adoption-private.json').read_text())
q=(HERE.parent/'kernel298/native-quiesce.py').read_text().replace('k298','k363').replace('stage=298','stage=363')
q=q.replace("(r/'k297-work/boot-id-private.txt')","Path("+repr(adopted['guard_path'])+")").replace("startswith('#297 ')","startswith('#298 ')")
(HERE/'native-quiesce.py').write_text(q)
s=(HERE.parent/'kernel298/restart-bootloader.py').read_text().replace('k298','k363').replace('stage=298','stage=363')
s=s.replace("(r/'k297-work/boot-id-private.txt')","Path("+repr(adopted['guard_path'])+")").replace("startswith('#297 ')","startswith('#298 ')")
(HERE/'restart-bootloader.py').write_text(s)
for name in ['flash-logdump.py']:
    s=(HERE.parent/'kernel298'/name).read_text()
    s=s.replace('==298','==363').replace('stage=298','stage=363')
    (HERE/name).write_text(s)
files={}
for key,path in [('candidate',P/'logdump-k363-candidate-private.img'),('rollback',P.parent/'kernel298/logdump-k298-candidate-private.img'),('firmware',P.parent/'kernel276/boot-partition-k276-cci-io.img')]:
    files[key]=dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
assert files['candidate']['sha256']==package['logdump_sha256'] and files['rollback']['sha256']==old['logdump_sha256']
(P/'deployment-lock-private.json').write_text(json.dumps(dict(files=files),indent=2)+'\n')
for name in ['native-quiesce.py','restart-bootloader.py','flash-logdump.py']:compile((HERE/name).read_text(),name,'exec')
print('Prepared single k298 -> k363 switch with k298 rollback; not requested yet.')
