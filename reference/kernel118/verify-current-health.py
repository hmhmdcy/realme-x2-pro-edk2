from pathlib import Path
import tarfile,hashlib,json,re
from datetime import datetime,timezone
out=Path('/mnt/e/edk2-samurai-out/kernel118')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118')
p=out/'current115-health-private.tar.gz'
with tarfile.open(p) as tf: d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in d['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
assert d['boot-id-private.txt']==(out.parent/'kernel115/final-boot-id-private.txt').read_bytes()
assert d['taint.txt'].strip()==b'0'
assert d['phosh.txt'].strip() and d['phoc.txt'].strip()
date_rows=[l for l in d['samples.txt'].decode().splitlines() if re.match(r'^20\d\d-',l) or l.endswith(' UTC 2026')]
assert len(date_rows)==10
start=datetime.fromisoformat(date_rows[0].replace('Z','+00:00')) if re.match(r'^20\d\d-',date_rows[0]) else datetime.strptime(date_rows[0],'%a %b %d %H:%M:%S UTC %Y').replace(tzinfo=timezone.utc)
assert int(d['finished-epoch.txt'])-int(start.timestamp())>=300
assert d['connector.txt'].strip()==b'connected'
assert d['pcm.txt'].strip()==b'closed\nclosed'
assert d['amps.txt'].count(b'powered=0')==2 and d['amps.txt'].count(b'muted=1')==2
assert d['slpi.txt'].strip()==b'offline' and d['sensor-power.txt'].strip()==b'vdd=0 vddio=0'
assert d['traces.txt'].strip()==b'0\n0'
for name,count in [('nv-verify.txt',6),('source-verify.txt',4),('vendor-verify.txt',1)]:
    assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
before=d['dmesg-before.txt'].decode();after=d['dmesg-after.txt'].decode()
report=dict(current_kernel=115,same_boot=True,archive_members_verified=True,observation_seconds=300,ten_native_samples_pass=True,phosh_phoc_drm_present=True,taint=0,pcm_closed_amps_idle=True,slpi_offline_sensor_power_off=True,nv6_source4_vendor_preserved=True,traces_off=True,total_dpu_timeouts=after.count('frame done timeout'),window_dpu_timeouts=after.count('frame done timeout')-before.count('frame done timeout'),total_gpu_faults=after.count('*** gpu fault'),window_gpu_faults=after.count('*** gpu fault')-before.count('*** gpu fault'),wifi_up=d['wlan.txt'].strip()==b'up',zram_active=b'/dev/zram0' in d['swaps.txt'],archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),idle_window_only=True,persistent_display_fix=False,goal_complete=False)
for folder in [out,ref]:(folder/'current115-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
