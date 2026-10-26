from pathlib import Path
import hashlib,json,tarfile,host
here=Path(__file__).resolve().parent
assert json.loads((here/'final-health-validation.json').read_text())['static_front_still_bound']
native=r'''
from pathlib import Path
import hashlib,json,os,shutil,tarfile
os.umask(0o077);root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-runtime/boot-id-private.txt').read_bytes()
fixture=json.loads((root/'k210-capture-monitor-fixture-r3/summary.json').read_text());assert fixture['monitor_resumed']
targets=sorted(p for p in root.iterdir() if p.name.startswith('k210') and not p.is_symlink() and (p.is_dir() or p.is_file()))
targets.append(root/'gnss-assist')
snapshot=Path('/tmp/k210-evidence-snapshot');snapshot.mkdir(mode=0o700)
files={}
for p in targets:
    for q in (p.rglob('*') if p.is_dir() else [p]):
        if not q.is_file() or q.is_symlink():continue
        name=str(q.relative_to(root));data=q.read_bytes();dest=snapshot/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        files[name]=hashlib.sha256(data).hexdigest()
destination=root/'k210-native-evidence-private.tar.gz';assert not destination.exists()
with tarfile.open(destination,'w:gz') as archive:
    for name in sorted(files):archive.add(snapshot/name,arcname=name,recursive=False)
print(json.dumps(dict(archive=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=90)
(host.PRIVATE/'evidence-export-manifest-private.json').write_bytes(p.stdout)
record=json.loads(p.stdout);target=host.PRIVATE/'native-evidence-private.tar.gz';assert not target.exists()
host.download(record['archive'],target);assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:
    members={item.name:hashlib.sha256(archive.extractfile(item).read()).hexdigest() for item in archive.getmembers() if item.isfile()}
assert members==record['files']
report=dict(stage=210,regular_files=len(members),consistent_snapshot_before_archiving=True,archive_hash_verified=True,all_regular_member_hashes_verified=True,raw_scene_images_and_private_identifiers_and_archive_fingerprints_not_published=True)
(here/'evidence-export-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
