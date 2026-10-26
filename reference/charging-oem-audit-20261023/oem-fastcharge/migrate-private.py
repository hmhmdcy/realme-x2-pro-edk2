"""Move only this candidate's original firmware/source and generated references."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent
DEST=Path('E:/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private').resolve()
EXPECTED=Path('E:/edk2-samurai-out/charging-management-20261023').resolve()
assert DEST.is_relative_to(EXPECTED) and HERE.name=='oem-fastcharge'
DEST.mkdir(exist_ok=True);(DEST/'test-output').mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=[]
for name in ['oem','oem-reference.c','oem-reference','array-true.c','array-false.c','array-true','array-false']:
 src=(HERE/name).resolve()
 assert src.is_relative_to(HERE.resolve())
 dst=DEST/'oem' if name=='oem' else DEST/'test-output'/name
 assert dst.resolve().is_relative_to(DEST)
 if src.exists():
  assert not dst.exists()
  before={str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()} if src.is_dir() else {'':sha(src)}
  shutil.move(str(src),str(dst))
  after={str(p.relative_to(dst)):sha(p) for p in dst.rglob('*') if p.is_file()} if dst.is_dir() else {'':sha(dst)}
  assert before==after
  receipt.append(dict(name=name,sha256=before,private_destination=str(dst)))
(HERE/'privacy-migration.json').write_text(json.dumps(dict(passed=True,moved=receipt,bytes_unchanged=True,phone_accessed=False),indent=2)+'\n')
print(json.dumps(dict(passed=True,moved=len(receipt))))
