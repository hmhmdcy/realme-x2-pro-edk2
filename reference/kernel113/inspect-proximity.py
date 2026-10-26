from pathlib import Path
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel113')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
archive = out / 'sensor-ram-v8.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'cbca21863ae5cc3b38481e4aa1bee4be19575e4f9f5dd689bb6dbf7cd96717e1'
with tarfile.open(archive) as tar:
    log = tar.extractfile('./proximity.txt').read().decode()
    exit_code = int(tar.extractfile('./proximity-exit.txt').read())
samples = re.findall(r'^Proximity sensor measurement: (FAR|NEAR)$', log, re.M)
name = re.search(r'  name: ([^\n]+)', log).group(1)
vendor = re.search(r'  vendor: ([^\n]+)', log).group(1)
assert exit_code == 0 and name == 'stk_stk3331' and vendor == 'sensortek'
assert samples == ['FAR'] and 'stream-type: on-change' in log
assert 'Sensor disable request sent successfully' in log
report = dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              query_exit=exit_code, sensor_name=name, vendor=vendor,
              data_type='proximity', stream_type='on-change',
              sample_count=len(samples), sample_states=sorted(set(samples)),
              real_sample_received=True, cover_uncover_verified=False,
              full_sensor_function_accepted=False)
(ref / 'proximity-v8-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(out / 'proximity-v8-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
