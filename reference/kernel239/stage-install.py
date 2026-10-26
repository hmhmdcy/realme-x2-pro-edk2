from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;archive=P/'r15-seven-package-repo-private.tar.gz';meta=json.loads((P/'seven-package-bundle-private.json').read_text());assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['sha256']
host.upload(archive,'/var/lib/samurai/k239-tools/r15-seven-package-repo-private.tar.gz')
code=r'''
from pathlib import Path
import hashlib,json,os,tarfile,sys
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
for kind in ['raw','rgb']:assert json.loads((r/('k239-front-r15-'+kind)/'summary.json').read_text())['passed']
archive=r/'k239-tools/r15-seven-package-repo-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==sys.argv[1]
target=r/'k239-r15-package-candidates';assert not target.exists();target.mkdir(mode=0o700)
with tarfile.open(archive,'r:gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  assert member.name=='forward-manifest.json' or member.name.startswith('forward/')
  path=target/member.name;path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);path.write_bytes(tar.extractfile(member).read());path.chmod(0o600)
manifest=json.loads((target/'forward-manifest.json').read_text());assert len(manifest['packages'])==7
for package in manifest['packages']:assert hashlib.sha256((target/'forward'/package['file']).read_bytes()).hexdigest()==package['sha256']
print(json.dumps(dict(stage=239,seven_signed_package_repo_staged=True,no_transaction_sent=True)))
'''
result=host.ssh('python3 - '+meta['sha256'],input=code.encode(),timeout=30);(P/'install-stage-host-private.log').write_bytes(result.stdout+result.stderr);print(result.stdout.decode().strip())
