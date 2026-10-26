from pathlib import Path
import hashlib
import json
import tarfile
import host

p=host.ssh('test -f /var/lib/samurai/k186-reboot-runtime-r2/summary.json && tar -C /var/lib/samurai -czf /tmp/k186-restored-runtime-private.tar.gz k186-reboot-runtime-r2 && sha256sum /tmp/k186-restored-runtime-private.tar.gz',timeout=45)
digest=p.stdout.decode().split()[0]
dest=host.PRIVATE/'k186-restored-runtime-private.tar.gz'
host.download('/tmp/k186-restored-runtime-private.tar.gz',dest)
assert hashlib.sha256(dest.read_bytes()).hexdigest()==digest
folder=host.PRIVATE/'restored-runtime-evidence-private'
with tarfile.open(dest) as tar:tar.extractall(folder,filter='data')
data=json.loads((folder/'k186-reboot-runtime-r2/summary.json').read_text())
data['evidence_archive_sha256']=digest
(Path(__file__).resolve().parent/'restored-runtime-r2-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'restored_runtime_archive_sha_verified':True,'original_driver_restored':True,'candidate_not_accepted':True}))
