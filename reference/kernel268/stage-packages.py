"""Stage signed native packages and save the current package database before preflight."""
from pathlib import Path
import json
import host

R=Path(__file__).resolve().parent;P=host.PRIVATE
meta=json.loads((R/'runtime-repo-validation.json').read_text())
host.upload(P/'r19-seven-package-repo-private.tar.gz','/var/lib/samurai/k268-tools/r19-seven-package-repo-private.tar.gz')
code=r'''
from pathlib import Path
import hashlib,json,os,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
archive=r/'k268-tools/r19-seven-package-repo-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==DIGEST
p=r/'k268-r19-package-candidates';p.mkdir(mode=0o700)
with tarfile.open(archive,'r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  assert m.name=='forward-manifest.json' or m.name.startswith('forward/')
  dest=p/m.name;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
manifest=json.loads((p/'forward-manifest.json').read_text());assert len(manifest['packages'])==7
for x in manifest['packages']:assert hashlib.sha256((p/'forward'/x['file']).read_bytes()).hexdigest()==x['sha256']
before=r/'k268-tools/installed-before-private.txt';assert not before.exists();before.write_bytes(Path('/lib/apk/db/installed').read_bytes())
print(json.dumps(dict(stage=268,seven_packages_and_signed_index_staged=True,current_database_saved=True,no_transaction_sent=True)))
'''.replace('DIGEST',repr(meta['sha256']))
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(P/'package-stage-private.json').write_bytes(q.stdout);print(q.stdout.decode())
