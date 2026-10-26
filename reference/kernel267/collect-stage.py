"""Keep exact module/config rollback files on the PC before reboot."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

R=Path(__file__).resolve().parent;P=host.PRIVATE
q=host.ssh('tar -czf - -C /var/lib/samurai k267-module-transaction k267-input',timeout=40)
p=P/'module-stage-private.tar.gz';assert not p.exists();p.write_bytes(q.stdout)
with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:gz') as tar:
    rows=json.load(tar.extractfile('k267-module-transaction/before-files-private.json'))
    for name,row in rows.items():
        data=tar.extractfile('k267-module-transaction/before/'+name.lstrip('/')).read()
        assert hashlib.sha256(data).hexdigest()==row['sha256']
proof=json.loads((R/'build-package-validation.json').read_text())
candidate=P/'boot-partition-k267-common-camera.img'
rollback=P.parent/'kernel235/boot-partition-k235-imx319-p-lab.img'
for file,digest in [(candidate,proof['boot_sha256']),(rollback,proof['rollback_boot_sha256'])]:
    assert hashlib.sha256(file.read_bytes()).hexdigest()==digest and file.stat().st_size==100663296
assert json.loads((P/'boot-config-private.json').read_text())['partitions']['boot']['sha256']==proof['rollback_boot_sha256']
lock=dict(stage=267,files=dict(boot_candidate=dict(path=str(candidate),sha256=proof['boot_sha256']),
 boot235_rollback=dict(path=str(rollback),sha256=proof['rollback_boot_sha256'])),
 module_backup_sha256=hashlib.sha256(q.stdout).hexdigest())
(P/'deployment-lock-private.json').write_text(json.dumps(lock,indent=2)+'\n')
report=dict(stage=267,pc_rollback_archive_verified=True,backup_files=len(rows),bytes=len(q.stdout),
 archive_sha256=lock['module_backup_sha256'],candidate_and_current_rollback_boot_verified=True)
(R/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
