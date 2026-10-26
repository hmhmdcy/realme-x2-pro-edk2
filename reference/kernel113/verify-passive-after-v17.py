from pathlib import Path
import hashlib,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'passive-after-v17-long-host-fetch.tar'
with tarfile.open(path) as archive:
    data={m.name.removeprefix('./'):archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
with tarfile.open(out/'reboot-audio-clean-13.tar') as archive:
    assert data['boot-id-private.txt']==archive.extractfile('./boot-id-private.txt').read()
uptime=float(data['state.txt'].split()[0]); assert uptime>=1800
assert data['state.txt'].splitlines()[-1]==b'0'
assert data['slpi.txt'].splitlines()==[b'offline',b'qcom/sm8150/realme/samurai/slpi.mdt']
assert data['sensor-power.txt'].strip()==b'vdd=0 vddio=0'
assert b'started' in data['greetd.txt'] and b'/etc/phosh/phoc.ini' in data['processes-private.txt']
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    matches_boot13=True,uptime_seconds=uptime,taint=0,
    dpu_timeouts=data['dmesg.txt'].count(b'frame done timeout'),
    gpu_faults=data['dmesg.txt'].count(b'*** gpu fault'),
    phosh_process_present=True,slpi_offline_sensor_power_off=True,
    visual_interaction_not_reconfirmed=True,long_term_display_fix_not_accepted=True,goal_complete=False)
(ref/'passive-after-v17-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
