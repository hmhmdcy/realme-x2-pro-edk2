"""Build a two-module PM-link update, preserving the actually booted payload."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

ref=Path(__file__).resolve().parent
root=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
out=root/'pm-update';out.mkdir(mode=0o700,exist_ok=True)
old=root/'service/samurai-charging-payload.tar.gz'
proof=json.loads((ref/'service-test-result.json').read_text())
assert hashlib.sha256(old.read_bytes()).hexdigest()==proof['payload_sha256']
saved=out/'boot-validated-payload-v2.tar.gz'
if not saved.exists():saved.write_bytes(old.read_bytes())
with tarfile.open(saved) as tar:before=json.loads(tar.extractfile('usr/share/samurai-charging/manifest.json').read())
after=json.loads(json.dumps(before));build=json.loads((ref/'integrated-build-result.json').read_text())
files={}
for name in ['samurai-mp2650','samurai-gauge-protection']:
    info=build['modules'][name];path=Path(info['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256']
    target=before['modules'][name]['target'];files[target.lstrip('/')]=path
    after['modules'][name]['sha256']=info['sha256'];after['installed_files'][target]=info['sha256']
assert before['modules']['samurai-usb-input']['sha256']==build['modules']['samurai-usb-input']['sha256']
meta=out/'manifest-v3.json';meta.write_text(json.dumps(after,indent=2)+'\n')
files['usr/share/samurai-charging/manifest.json']=meta
archive=out/'pm-link-update.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name,p in files.items():tar.add(p,arcname=name,recursive=False)
report={'old_payload_sha256':proof['payload_sha256'],'old_manifest':before,
    'new_manifest':after,'updated_files':list(files),'native_usb_provider_unchanged':True,
    'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'installed':False}
(out/'update-lock.json').write_text(json.dumps(report,indent=2)+'\n')
(ref/'pm-update-build-result.json').write_text(json.dumps({k:v for k,v in report.items() if k not in ['old_manifest','new_manifest']},indent=2)+'\n')
print(json.dumps({'pm_link_update_prepared':True,'only_two_modules_and_manifest':True,'archive_sha256':report['archive_sha256']}))
