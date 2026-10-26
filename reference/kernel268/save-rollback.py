"""Verify the seven current signed APKs and copy rollback evidence to the PC."""
from pathlib import Path
import hashlib
import io
import json
import tarfile
import host

R=Path(__file__).resolve().parent;P=host.PRIVATE
code=r'''
from pathlib import Path
import hashlib,json,subprocess
r=Path('/var/lib/samurai');p=r/'k239-r15-package-candidates'
m=json.loads((p/'forward-manifest.json').read_text());assert len(m['packages'])==7
for row in m['packages']:
 file=p/'forward'/row['file'];assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
 q=subprocess.run(['apk','verify',str(file)],capture_output=True);assert q.returncode==0
assert (p/'forward/packages.adb').is_file()
print(json.dumps(dict(stage=268,seven_original_apks_present_and_trusted=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30);assert json.loads(q.stdout)['seven_original_apks_present_and_trusted']
q=host.ssh('tar -czf - -C /var/lib/samurai k268-r19-package-transaction k239-r15-package-candidates/forward k239-r15-package-candidates/forward-manifest.json',timeout=40)
p=P/'r15-rollback-and-preflight-private.tar.gz';assert not p.exists();p.write_bytes(q.stdout)
with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:gz') as tar:
    manifest=json.load(tar.extractfile('k239-r15-package-candidates/forward-manifest.json'))
    for row in manifest['packages']:
        data=tar.extractfile('k239-r15-package-candidates/forward/'+row['file']).read()
        assert hashlib.sha256(data).hexdigest()==row['sha256']
report=dict(stage=268,original_seven_apks_verified_on_phone_and_pc=True,preflight_world_repositories_and_db_saved=True,
 bytes=len(q.stdout),archive_sha256=hashlib.sha256(q.stdout).hexdigest())
(R/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
