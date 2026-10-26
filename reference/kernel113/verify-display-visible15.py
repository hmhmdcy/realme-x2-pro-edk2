from pathlib import Path
import hashlib,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'display-visible15.tar'
with tarfile.open(path) as archive:
    data={entry.name.removeprefix('./'):archive.extractfile(entry).read() for entry in archive if entry.isfile()}
count=0
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
    count+=1
change=json.loads(data['change.json'])
assert change['before']=='uint32 60' and change['after']=='uint32 0'
assert data['idle-delay-before.txt'].strip()==b'uint32 60' and data['idle-delay-after.txt'].strip()==b'uint32 0'
assert b'Enabled: yes' in data['output-after.txt']
before=data['dmesg-before.txt'];after=data['dmesg-after.txt']
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nested_files_verified=count,
    boot_checkpoint='reboot-audio-clean-15',original_idle_delay_seconds=60,bringup_idle_delay_seconds=0,
    original_setting_saved=True,setting_restoration_pending=True,
    taint_before=int(data['taint-before.txt']),taint_after=int(data['taint-after.txt']),
    output_enabled=True,new_dpu_timeouts=after.count(b'frame done timeout')-before.count(b'frame done timeout'),
    new_gpu_faults=after.count(b'*** gpu fault')-before.count(b'*** gpu fault'),
    unlock_credentials_unchanged=True,permanent_display_fix_accepted=False,goal_complete=False)
(ref/'display-visible15-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
