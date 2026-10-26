from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,io,json,os,subprocess,tarfile
root=Path('/var/lib/samurai');base=root/'k214-baseline';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
db=(base/'apk-installed-before-private.txt').read_bytes();assert db==Path('/lib/apk/db/installed').read_bytes();original=json.loads((base/'original-files-manifest-private.json').read_text())
metadata={}
for entry in db.decode().split('\n\n'):
    fields={line[0]:line[2:] for line in entry.splitlines() if len(line)>1 and line[1]==':' and line[0] in ['P','V','A','L','U','T','D','p','o','m','t','c','i','r']}
    if fields.get('P') in ['libcamera','libcamera-ipa','libcamera-tools']:
        assert fields['V']=='99990.7.2-r4';names=[]
        for name in subprocess.check_output(['apk','info','-L',fields['P']],text=True).splitlines()[1:]:
            name=name.strip()
            if not name:continue
            assert not name.startswith('/') and '..' not in Path(name).parts
            if name in original:names.append(name)
            else:assert Path('/',name).is_dir()
        metadata[fields['P']]=dict(fields=fields,files=names)
assert len(metadata)==3
destination=Path('/tmp/k214-camera-rollback-inputs-private.tar.gz');assert not destination.exists();members={}
with tarfile.open(destination,'w:gz') as archive:
    items={'metadata-private.json':json.dumps(metadata,indent=2).encode(),'original-files-manifest-private.json':json.dumps(original,indent=2).encode()}
    for name,record in original.items():
        if record['kind']=='file':
            data=(base/'files'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==record['sha256'];items['files/'+name]=data
    for name,data in items.items():
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600;archive.addfile(info,io.BytesIO(data));members[name]=hashlib.sha256(data).hexdigest()
print(json.dumps(dict(path=str(destination),size=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),members=members)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60);record=json.loads(p.stdout);(host.PRIVATE/'rollback-snapshot-archive-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'rollback-snapshot-inputs-private.tar.gz';assert not target.exists()
with target.open('xb') as output:
    for offset in range(0,record['size'],65536):
        p=host.ssh('dd if=/tmp/k214-camera-rollback-inputs-private.tar.gz bs=65536 skip='+str(offset//65536)+' count=1',timeout=30);assert len(p.stdout)==min(65536,record['size']-offset);output.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:
    members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()};assert members==record['members']
    metadata=json.loads(archive.extractfile('metadata-private.json').read())
(host.PRIVATE/'rollback-snapshot-metadata-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
report=dict(stage=214,original_installed_r4_camera_snapshot_retrieved=True,current_same_boot_and_unchanged_database_verified=True,all_snapshot_file_hashes_verified=True,three_package_metadata_and_file_ownership_saved=True,source='authoritative214 device backup, not unverified cached archive',cached_original_apks_not_accepted_due_to_unavailable_signing_key=True,all_snapshot_members_verified=len(members),private_inputs_not_published=True,no_device_mutation=True)
(here/'rollback-snapshot-inputs-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
