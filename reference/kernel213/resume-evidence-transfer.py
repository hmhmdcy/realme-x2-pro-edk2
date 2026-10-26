from pathlib import Path
import hashlib,host,json,tarfile
here=Path(__file__).resolve().parent;private=host.PRIVATE
record=json.loads((private/'final-evidence-manifest-private.json').read_text());target=private/'final-evidence-private.tar.gz';offset=target.stat().st_size
assert 0<offset<record['size'] and offset%131072==0
code=r'''
from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
path=Path('/tmp/k213-final-evidence-private.tar.gz');data=path.read_bytes();print(json.dumps(dict(size=len(data),sha256=hashlib.sha256(data).hexdigest(),prefix_sha256=hashlib.sha256(data[:OFFSET]).hexdigest())))
'''.replace('OFFSET',str(offset))
p=None
for attempt in range(3):
    try:p=host.ssh('python3 -',input=code.encode(),timeout=30);break
    except RuntimeError:
        if attempt==2:raise
assert p is not None;remote=json.loads(p.stdout)
assert remote['size']==record['size'] and remote['sha256']==record['sha256'] and remote['prefix_sha256']==hashlib.sha256(target.read_bytes()).hexdigest()
state=dict(initial_1mib_transfer_truncated=True,verified_prefix_bytes=offset,archive_generation_not_repeated=True,chunk_bytes=131072,retries=0,completed=False)
(private/'evidence-transfer-recovery-private.json').write_text(json.dumps(state,indent=2)+'\n')
with target.open('ab') as destination:
    count=0
    while offset<record['size']:
        data=None
        for attempt in range(3):
            try:
                p=host.ssh('dd if='+record['path']+' bs=131072 skip='+str(offset//131072)+' count=1',timeout=30)
                assert len(p.stdout)==min(131072,record['size']-offset)
                data=p.stdout;break
            except (RuntimeError,AssertionError):
                state['retries']+=1
                (private/'evidence-transfer-recovery-private.json').write_text(json.dumps(state,indent=2)+'\n')
        assert data is not None,'Read-only recovery exhausted; preserve verified prefix for continuation'
        destination.write(data);destination.flush();offset+=len(data);count+=1
        if count%16==0:print(json.dumps(dict(transfer_progress_bytes=offset,total_bytes=record['size'])),flush=True)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
with tarfile.open(target) as archive:members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
assert members==record['files'];state.update(completed=True,all_members_verified=True)
(private/'evidence-transfer-recovery-private.json').write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=213,private_archive_all_members_verified=True,archived_regular_files=len(members),raw_scene_images_and_logs_kept_private=True,isolated_sdk_and_ipa_private_key_excluded=True,candidate_binaries_and_build_logs_preserved=True,initial_one_mib_transfer_truncated=True,verified_existing_prefix_and_resumed_128kib_chunks=True,read_retry_count=state['retries'],clean_current_boot=True,initial_fetch_configure_link_probe_and_sensor_pattern_failures_preserved=True)
(here/'final-evidence-archive-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
