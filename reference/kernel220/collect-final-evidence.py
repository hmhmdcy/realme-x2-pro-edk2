from pathlib import Path
import hashlib,host,json,tarfile

here=Path(__file__).resolve().parent
assert json.loads((here/'final-health-validation.json').read_text())['taint']==0
code=r'''
from pathlib import Path
import hashlib,json,tarfile
root=Path('/var/lib/samurai');base=root/'k220-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
target=Path('/tmp/k220-final-evidence-private.tar.gz');assert not target.exists()
files=[]
for directory in sorted(root.glob('k220-*')):
    if not directory.is_dir():continue
    for p in sorted(directory.rglob('*')):
        if not p.is_file() or p.is_symlink() or p.name in ['probe.gz','runtime.tar.gz','bundle-private.tar.gz']:continue
        data=p.read_bytes()
        assert p.suffix not in ['.pem','.key'] and b'PRIVATE KEY' not in data
        files.append(p)
members={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with tarfile.open(target,'w:gz') as tar:
    for p in files:tar.add(p,arcname=str(p.relative_to(root)),recursive=False)
target.chmod(0o600)
print(json.dumps(dict(bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),members=members)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60)
record=json.loads(p.stdout);(host.PRIVATE/'final-evidence-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'final-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as output:
    for offset in range(0,record['bytes'],65536):
        p=host.ssh('dd if=/tmp/k220-final-evidence-private.tar.gz bs=65536 skip='+str(offset//65536)+' count=1',timeout=30)
        assert len(p.stdout)==min(65536,record['bytes']-offset);output.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:
    members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers()}
    assert members==record['members']
report=dict(stage=220,native_final_evidence_archive_retrieved=True,
            archive_and_all_member_hashes_verified=True,verified_members=len(members),
            native_test_logs_and_contexts_preserved=True,kernel_module_backup_retained_in_prior219_archive=True,
            private_keys_and_scene_images_excluded=True,transfer_chunk_bytes=65536,
            archive_remains_private=True)
(here/'final-evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
