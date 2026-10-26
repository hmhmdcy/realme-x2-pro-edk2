from pathlib import Path
import hashlib,json,re,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(out/'nm-auto-restart-private.tar.gz') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 sha,name=line.split(None,1);assert hashlib.sha256(data[name.strip().removeprefix('./')]).hexdigest()==sha
assert data['exit.txt']==b'0\n' and data['result.txt']==b'PASS\n' and data['taint.txt']==b'0\n'
assert data['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
assert data['uuid-after-private.txt'].decode().strip()==json.loads((out/'wifi-profile-deployment-private.json').read_text())['uuid']
assert data['phosh.txt'].strip() and data['phoc.txt'].strip() and data['remoteprocs.txt']==b'running\nrunning\n'
before=data['dmesg-before-private.txt'];after=data['dmesg-after-private.txt'];assert after.startswith(before)
patterns=['failed to install key','firmware crashed','frame done timeout','*** gpu fault','Call trace:']
assert all(after.count(p.encode())==before.count(p.encode()) for p in patterns)
http=data['https-result.txt'].decode().split();assert len(http)==3 and http[0]=='200' and int(http[1])==len(data['https-body.txt'])>0
samples=[float(l.split()[0]) for l in data['samples.txt'].decode().splitlines()];assert len(samples)==6 and samples[-1]-samples[0]>=25
freq=float(re.search(r'freq: ([\d.]+)',data['link-after-private.txt'].decode())[1]);assert freq in [2462,5180]
report=dict(kernel128_current_boot_verified=True,networkmanager_service_restart_success=True,
 automatic_connect_without_explicit_activation=True,connected_attempt=int(data['connected-attempt.txt']),
 automatic_frequency_mhz=freq,persistent_same_uuid_dual_band_profile_used=True,
 https_status=200,https_bytes=int(http[1]),samples=6,stable_window_seconds=round(samples[-1]-samples[0],2),
 desktop_modem_audio_stayed_running=True,new_key_gpu_dpu_firmware_calltrace_faults=0,taint=0,
 physical_coldboot_suspend_and_longrun_not_verified=True,goal_complete=False)
(ref/'nm-auto-restart-validation.json').write_text(json.dumps(report,indent=2)+'\n')
profile=json.loads((ref/'wifi-profile-validation.json').read_text());profile.update(full_networkmanager_restart_pending=False,full_networkmanager_restart_auto_connect_pass=True,automatic_frequency_mhz=freq)
(ref/'wifi-profile-validation.json').write_text(json.dumps(profile,indent=2)+'\n');print(json.dumps(report),flush=True)
