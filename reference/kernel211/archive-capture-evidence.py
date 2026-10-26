from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,io,json,os,subprocess,tarfile
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
log=subprocess.check_output(['dmesg']);warnings=[line for line in log.splitlines() if b'WARNING:' in line]
assert len(warnings)==349 and all(b'__arm_lpae_unmap' in line and b'drivers/iommu/io-pgtable-arm.c:673' in line for line in warnings)
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
destination=Path('/tmp/k211-capture-evidence-private.tar.gz');assert not destination.exists()
files={}
with tarfile.open(destination,'w:gz') as archive:
    for folder in sorted(root.glob('k211-*')):
        if not folder.is_dir() or folder.is_symlink():continue
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.is_symlink():continue
            data=path.read_bytes();name=str(path.relative_to(root));info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600
            archive.addfile(info,io.BytesIO(data));files[name]=hashlib.sha256(data).hexdigest()
print(json.dumps(dict(path=str(destination),size=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),files=files)))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=100);record=json.loads(p.stdout)
(host.PRIVATE/'capture-evidence-manifest-private.json').write_bytes(p.stdout)
target=host.PRIVATE/'capture-evidence-private.tar.gz';assert not target.exists()
with target.open('xb') as destination:
    for offset in range(0,record['size'],1024*1024):
        p=host.ssh('dd if='+record['path']+' bs=1048576 skip='+str(offset//1048576)+' count=1',timeout=50)
        assert len(p.stdout)==min(1024*1024,record['size']-offset);destination.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=211,private_native_snapshot_created=True,archived_regular_files=len(members),private_archive_all_members_verified=True,raw_scene_images_and_logs_private=True,transfer_in_one_mib_chunks=True,recorded_gpu_unmap_warnings=349,taint=512,not_a_clean_boot_pass=True)
(here/'capture-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
