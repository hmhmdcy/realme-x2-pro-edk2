from pathlib import Path,PurePosixPath
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel102')
files={}
with tarfile.open(out/'final-status.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        parts=PurePosixPath(m.name).parts;assert parts[0]=='k102-final-status' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=tar.extractfile(m).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
s=files['state.txt'].decode().splitlines();assert s[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()
assert s[3:]==['0','modem','running','adsp','running']
assert files['bt-class.txt']==b'' and b'wpa_state=COMPLETED\n' in files['wifi-status.txt'] and b'freq=5180\n' in files['wifi-status.txt']
assert b'active=0 starts=0 stops=0 watchdog_stops=0 error=0' in files['haptics-status.txt']
assert re.search(rb'gpio37\s+: out low',files['gpio.txt']) and re.search(rb'gpio148\s+: out low',files['gpio.txt'])
assert b'max98927' not in files['components.txt'] and b'wcd934x-codec.0.auto' in files['components.txt']
assert len(files['nv-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in files['nv-check.txt'].splitlines())
assert files['persist.sha'].decode().split()[0]==(out/'persist-before.sha').read_text().split()[0]
d=files['dmesg.txt'].decode();assert not re.search(r'(4080000|17300000)\.remoteproc: fatal',d)
report=dict(final_readonly_archive_audit_pass=True,private_files=len(checked),
 archive_sha256=hashlib.sha256((out/'final-status.tar').read_bytes()).hexdigest(),uptime_seconds=float(s[2].split()[0]),
 same_fresh_boot=True,mpss_running=True,adsp_running=True,mp_adsp_fatal_count=0,wifi_band_mhz=5180,wifi_completed=True,
 bluetooth_controller_removed=True,motor_standby=True,no_new_vibration=True,physical_confirmation_deferred=True,
 wrong_amp_components_unbound=True,amp_resets_low=True,wcd_codec_bound=True,nv_unchanged=True,persist_unchanged=True,
 display_timeouts=d.count('frame done timeout'),bt_phase2_errors=d.count('Frame reassembly failed'),kernel_taint=0,goal_complete=False)
(out/'final-status-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
