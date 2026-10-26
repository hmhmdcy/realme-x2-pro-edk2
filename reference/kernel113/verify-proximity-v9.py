from pathlib import Path
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
archive=out/'sensor-ram-v9.tar'
with tarfile.open(archive) as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
with tarfile.open(out/'reboot-radio-clean-4.tar') as tar:
    assert tar.extractfile('./boot-id-private.txt').read()==data['boot-id-private.txt']
log=data['proximity.txt'].decode()
assert int(data['proximity-exit.txt'])==0
assert '  name: stk_stk3331' in log and '  vendor: sensortek' in log
assert 'Sensor disable request sent successfully' in log
samples=re.findall(r'^Proximity sensor measurement: (FAR|NEAR)$', log, re.M)
assert samples[0]==samples[-1]=='FAR' and len(samples)>=9
changes=sum(a!=b for a,b in zip(samples,samples[1:]))
assert changes>=8 and set(samples)=={'NEAR','FAR'}
times=[]; last=None
for line in log.splitlines():
    if 'Message 769 for sensor' in line:
        stamp=re.search(r'(\d\d):(\d\d):(\d\d\.\d+): Message',line)
        if stamp: last=sum(float(value)*factor for value,factor in zip(stamp.groups(),(3600,60,1)))
    if line.startswith('Proximity sensor measurement:'):
        assert last is not None
        times.append(last)
assert len(times)==len(samples)
intervals=[round(b-a,3) for a,b in zip(times,times[1:])]
report=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),kernel_build=113,
            boot_checkpoint='reboot-radio-clean-4', sensor_name='stk_stk3331',vendor='sensortek',
            query_exit=0,sample_count=len(samples),state_changes=changes,
            near_samples=samples.count('NEAR'),far_samples=samples.count('FAR'),
            first_state=samples[0],last_state=samples[-1],
            minimum_interval_seconds=min(intervals),maximum_interval_seconds=max(intervals),
            user_cover_uncover_and_display_operation_confirmed=True,
            proximity_function_accepted=True,all_sensors_accepted=False)
(ref/'proximity-v9-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'proximity-v9-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
