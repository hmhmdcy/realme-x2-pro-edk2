from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
assert json.loads((here/'final-health-validation.json').read_text())['taint']==0
assert json.loads((here/'installed-rollback-readiness-validation.json').read_text())['real_rollback_not_sent']
code=r'''
from pathlib import Path
import hashlib,io,json,os,re,tarfile
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k214-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
destination=Path('/tmp/k214-final-evidence-private.tar.gz');assert not destination.exists();members={}
with tarfile.open(destination,'w:gz') as archive:
    for directory in sorted(root.glob('k214-*')):
        assert directory.is_dir()
        for path in sorted(directory.rglob('*')):
            if not path.is_file() or path.is_symlink() or path.suffix=='.apk' or path.name=='bundle-private.tar.gz' or '/probes/' in str(path):continue
            assert path.suffix not in ['.pem','.rsa'] and 'ipa-priv-key' not in path.name
            data=path.read_bytes();assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',data)
            name=str(path.relative_to(root));members[name]=hashlib.sha256(data).hexdigest()
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600;archive.addfile(info,io.BytesIO(data))
print(json.dumps(dict(path=str(destination),bytes=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),members=members)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60);record=json.loads(p.stdout);(host.PRIVATE/'final-evidence-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'final-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as output:
    for offset in range(0,record['bytes'],65536):
        p=host.ssh('dd if=/tmp/k214-final-evidence-private.tar.gz bs=65536 skip='+str(offset//65536)+' count=1',timeout=30);assert len(p.stdout)==min(65536,record['bytes']-offset);output.write(p.stdout)
        if offset//65536%20==0:print(json.dumps(dict(retrieved_bytes=offset+len(p.stdout),total_bytes=record['bytes'])),flush=True)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:
    members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers()};assert members==record['members']
report=dict(stage=214,native_final_evidence_archive_retrieved=True,transfer_chunk_bytes=65536,archive_and_all_member_hashes_verified=True,verified_members=len(members),private_key_files_and_material_excluded=True,scene_images_not_collected=True,archive_stays_private=True,large_transport_root_cause_not_claimed_fixed=True)
(here/'final-evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
