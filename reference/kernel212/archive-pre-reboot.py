from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
proof=json.loads((host.PRIVATE/'quiesce-validation-private.json').read_text());assert proof['quiesce_audit_pass'] and proof['known_gpu_unmap_warnings']==349
code=r'''
from pathlib import Path
import hashlib,io,json,tarfile
exec(Path('/tmp/k212-warning-guard.py').read_text())
root=Path('/var/lib/samurai');destination=Path('/tmp/k212-prewarmboot-private.tar.gz');assert not destination.exists();files={}
with tarfile.open(destination,'w:gz') as archive:
    for folder in sorted(root.glob('k212-*')):
        if not folder.is_dir() or folder.is_symlink():continue
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.is_symlink():continue
            data=path.read_bytes();name=str(path.relative_to(root));info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
            archive.addfile(info,io.BytesIO(data));files[name]=hashlib.sha256(data).hexdigest()
print(json.dumps(dict(path=str(destination),size=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60);record=json.loads(p.stdout);(host.PRIVATE/'prewarmboot-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'prewarmboot-private.tar.gz';assert not target.exists()
with target.open('xb') as destination:
    for offset in range(0,record['size'],1048576):
        p=host.ssh('dd if='+record['path']+' bs=1048576 skip='+str(offset//1048576)+' count=1',timeout=40);assert len(p.stdout)==min(1048576,record['size']-offset);destination.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=212,private_archive_all_members_verified=True,archived_regular_files=len(members),orderly_quiesce_completed=True,no_transition_yet_sent=True,partitions_flashed=[])
(here/'prewarmboot-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
