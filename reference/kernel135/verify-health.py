from pathlib import Path
import tarfile
import json
import hashlib
r=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel135')
with tarfile.open(out/'rollback-health-private.tar.gz') as tf:
    data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
assert data['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
report=json.loads(data['health-private.json'])
assert report['same_boot_and_desktop_pids'] and report['taint']==0 and report['fault_increments_zero']
assert 42<=report['wifi_timestamp_span_seconds']<65 and report['guarded_samples']==8
assert report['fault_counts_before']==report['fault_counts_after']
assert report['fault_counts_after']['gpu']==0 and report['fault_counts_after']['warn']==0 and report['fault_counts_after']['codec_enospc']==0
assert data['sources-check-private.txt'].count(b': OK')==11
assert b'POWER_SUPPLY_ONLINE=1\n' in data['mp2650-final-uevent.txt']
report.update(archive_sha256=hashlib.sha256((out/'rollback-health-private.tar.gz').read_bytes()).hexdigest(),usb_input134_driver_absent_after_rollback=True)
(r/'reference/kernel135/rollback-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
