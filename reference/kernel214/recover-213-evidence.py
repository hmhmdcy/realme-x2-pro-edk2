from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent;old_private=host.PRIVATE.parent/'kernel213';record=json.loads((old_private/'final-evidence-manifest-private.json').read_text());target=old_private/'final-evidence-private.tar.gz';offset=target.stat().st_size;assert 0<offset<record['size'] and offset%65536==0
code=r'''
from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
data=Path('/tmp/k213-final-evidence-private.tar.gz').read_bytes();print(json.dumps(dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),prefix_sha256=hashlib.sha256(data[:OFFSET]).hexdigest())))
'''.replace('OFFSET',str(offset))
p=host.ssh('python3 -',input=code.encode(),timeout=30);remote=json.loads(p.stdout);assert remote['size']==record['size'] and remote['sha256']==record['sha256'] and remote['prefix_sha256']==hashlib.sha256(target.read_bytes()).hexdigest()
start=offset
with target.open('ab') as output:
    chunks=0
    while offset<record['size']:
        p=host.ssh('dd if=/tmp/k213-final-evidence-private.tar.gz bs=65536 skip='+str(offset//65536)+' count=1',timeout=30);assert len(p.stdout)==min(65536,record['size']-offset);output.write(p.stdout);output.flush();offset+=len(p.stdout);chunks+=1
        if chunks%16==0:print(json.dumps(dict(recovered_bytes=offset,total_bytes=record['size'])),flush=True)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files']
report=dict(stage=214,previous213_archive_recovered=True,same_boot_fresh_strict_usb_key_verified=True,existing_partial_prefix_hash_verified=True,resumed_64kib_chunks=True,archived_regular_files=len(members),whole_archive_and_all_members_verified=True,initial213_transfer_failures_preserved=True,raw_scene_images_logs_and_archive_fingerprints_kept_private=True,no_device_mutation=True)
(here/'previous-evidence-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
