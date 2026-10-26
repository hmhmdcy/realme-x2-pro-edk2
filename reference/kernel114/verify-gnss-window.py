from pathlib import Path
import hashlib, json, tarfile

p=Path('/mnt/e/edk2-samurai-out/kernel114/gnss-window-private.tar.gz')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='41a26d8ca7c0a266c745b8a3dcd172c2fcf1d87d6627629cb8cf9f81bf5faa8f'
with tarfile.open(p) as tar:
    files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==digest
assert int(files['start-result.txt'])==int(files['stop-result.txt'])==0
assert 'Successfully started' in files['start-private.txt'].decode()
assert 'Successfully stopped' in files['stop-private.txt'].decode()
monitor=files['monitor-private.txt'].decode()
assert monitor.strip()=='cancelling the operation...'
assert files['nv-check.txt'].decode().count(': OK')==6
assert files['source-check.txt'].decode().count(': OK')==4
report=dict(archive_and_member_hashes_verified=True,start_and_stop_requests_succeeded=True,
            monitor_window_seconds=55,monitor_return_code=int(files['monitor-result.txt']),
            position_or_satellite_events_received=False,location_fix_verified=False,
            engine_session_stop_acknowledged=True,nv_sources_unchanged=True,
            slpi_offline_sensor_power_off=files['state-after.txt'].decode().strip()=='offline\nvdd=0 vddio=0\n512',
            no_timeout_return_code_does_not_imply_position_success=True,goal_complete=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/gnss-window-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
