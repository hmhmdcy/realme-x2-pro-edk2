"""Freeze the two-file USB FLOAT fix; no device or restart action."""
from pathlib import Path
import copy
import gzip
import hashlib
import io
import json
import tarfile

REF=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
old_bytes=(PRIVATE/'r6-candidate/manifest.json').read_bytes()
assert sha(old_bytes)=='944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'
old=json.loads(old_bytes)
build=json.loads((REF/'source-float-build-result.json').read_bytes())
assert build['passed'] and not build['installed'] and not build['configuration_differences']
ko=Path(build['module']).read_bytes()
assert sha(ko)==build['module_sha256']=='7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70'
new=copy.deepcopy(old);new['adapter_revision']='r7'
target=new['modules']['samurai-usb-input']['target']
new['modules']['samurai-usb-input']['sha256']=sha(ko)
new['installed_files'][target]=sha(ko)
assert old['installed_files'][target]=='c77724ba582f66905ca08d1b185926a540691bd559614d20fa574d4b35492e3e'
assert {p for p in new['installed_files'] if new['installed_files'][p]!=old['installed_files'][p]}=={target}
for module in ['samurai-mp2650','samurai-gauge-protection']:assert old['modules'][module]==new['modules'][module]
manifest=(json.dumps(new,indent=2)+'\n').encode()
files={target:ko,'/usr/share/samurai-charging/manifest.json':manifest}
tar_raw=io.BytesIO()
with tarfile.open(fileobj=tar_raw,mode='w') as archive:
    for name,raw in sorted(files.items()):
        entry=tarfile.TarInfo(name.lstrip('/'));entry.uid=entry.gid=0;entry.uname=entry.gname='root'
        entry.mode=0o600;entry.size=len(raw);entry.mtime=0;archive.addfile(entry,io.BytesIO(raw))
compressed=io.BytesIO()
with gzip.GzipFile(filename='',mode='wb',fileobj=compressed,mtime=0) as stream:stream.write(tar_raw.getvalue())
payload=compressed.getvalue();out=PRIVATE/'r7-candidate';out.mkdir(exist_ok=True)
def freeze(name,raw):
    p=out/name
    if p.exists():assert p.read_bytes()==raw,'new bytes require a new revision: '+name
    else:p.write_bytes(raw)
freeze('manifest.json',manifest);freeze('samurai-usb-input.ko',ko);freeze('source-float-payload.tar.gz',payload)
report={'phase':'offline-payload-preparation','installed':False,'restart_executed':False,
        'old_manifest_sha256':sha(old_bytes),'new_manifest_sha256':sha(manifest),
        'payload_sha256':sha(payload),'payload_bytes':len(payload),
        'changed_files':{p:{'sha256':sha(raw),'mode':'0o600'} for p,raw in files.items()},
        'source_build_receipt_sha256':sha((REF/'source-float-build-result.json').read_bytes()),
        'source_test_receipt_sha256':build['test_receipt_sha256'],
        'charger_service_protection_boot_unchanged':True,
        'activation':'next coordinated boot; resident old provider must not be force-unloaded',
        'runtime_validation_pending':True}
raw=(json.dumps(report,indent=2)+'\n').encode();freeze('payload-result.json',raw)
(REF/'r7-payload-result.json').write_bytes(raw)
print(json.dumps(report,indent=2))
