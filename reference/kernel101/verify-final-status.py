from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel101')
sha=lambda b:hashlib.sha256(b).hexdigest()
files={}
with tarfile.open(out/'final-status.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        parts=PurePosixPath(m.name).parts
        assert parts[0]=='k101-final-status' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=tar.extractfile(m).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and sha(files[name])==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
s=files['state.txt'].decode().splitlines()
assert '#100 SMP PREEMPT' in s[0] and s[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()
assert s[3:]==['0','running','running']
assert b'wpa_state=COMPLETED\n' in files['wifi-status.txt'] and b'freq=5180\n' in files['wifi-status.txt']
assert files['native-api.txt']==b'native_version_reply service4_api=7 service4_branch=0 service7_api=2 service7_branch=0\n'
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
p=bytes.fromhex(re.search(rb'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-info.txt'])[1].decode())
assert len(p)==280 and int.from_bytes(p[13:17],'little')&0x1b==0
assert len(files['nv-check.txt'].splitlines())==6 and all(line.endswith(b': OK') for line in files['nv-check.txt'].splitlines())
assert files['persist.sha'].decode().split()[0]==(out/'persist-before.sha').read_text().split()[0]
d=files['dmesg.txt'].decode()
report=dict(final_status_audit_pass=True,kernel_build=100,verified_files=len(checked),
  archive_sha256=sha((out/'final-status.tar').read_bytes()),uptime_seconds=float(s[2].split()[0]),
  adsp_running=True,mpss_running=True,native_cached_version_matches=True,five_ghz_completed=True,bluetooth_all_four_flags_off=True,
  motor_standby=True,nv_unchanged=True,persist_unchanged=True,kernel_taint=0,
  mpss_fatal_count=len(re.findall(r'4080000\.remoteproc: fatal',d)),
  adsp_fatal_count=len(re.findall(r'17300000\.remoteproc: fatal',d)),display_timeouts=d.count('frame done timeout'),
  bt_phase_errors=d.count('Frame reassembly failed'),physical_vibration_deferred_by_user=True,goal_complete=False)
(out/'final-status-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
