from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
assert json.loads((here/'final-health-validation.json').read_text())['taint']==0
code=r'''
from pathlib import Path
import hashlib,io,json,os,subprocess,tarfile
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k212-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
log=subprocess.check_output(['dmesg']);assert all(log.count(term)==0 for term in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'Frame reassembly failed'])
destination=Path('/tmp/k212-final-evidence-private.tar.gz');assert not destination.exists();files={}
with tarfile.open(destination,'w:gz') as archive:
    for folder in sorted(root.glob('k212-*')):
        if not folder.is_dir() or folder.is_symlink():continue
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.is_symlink():continue
            data=path.read_bytes();name=str(path.relative_to(root));info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
            archive.addfile(info,io.BytesIO(data));files[name]=hashlib.sha256(data).hexdigest()
print(json.dumps(dict(path=str(destination),size=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);record=json.loads(p.stdout);(host.PRIVATE/'final-evidence-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'final-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as destination:
    for offset in range(0,record['size'],1048576):
        p=host.ssh('dd if='+record['path']+' bs=1048576 skip='+str(offset//1048576)+' count=1',timeout=50);assert len(p.stdout)==min(1048576,record['size']-offset);destination.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=212,private_archive_all_members_verified=True,archived_regular_files=len(members),raw_scene_images_and_logs_kept_private=True,transfer_in_one_mib_chunks=True,clean_current_boot=True,known211_failures_preserved_separately=True)
(here/'final-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
