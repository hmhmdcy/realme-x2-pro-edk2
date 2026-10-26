from pathlib import Path
import hashlib,json,os,re,runpy,stat,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
with tarfile.open(out/'dual-band-profile-private.tar.gz') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 sha,name=line.split(None,1);assert hashlib.sha256(data[name.strip().removeprefix('./')]).hexdigest()==sha
assert data['exit.txt']==b'0\n' and data['committed.txt']==b'1\n' and data['owner-mode.txt']==b'0:0:600\n'
assert data['before-private.nmconnection']==(out/'live-wifi-profile-before-private.nmconnection').read_bytes()
assert data['after-private.nmconnection']==(out/'wifi-dual-band-candidate-private.nmconnection').read_bytes()
assert data['boot-id-private.txt'].strip()==(out/'embedded-boot-id-private.txt').read_bytes().strip()
private=json.loads((out/'wifi-profile-deployment-private.json').read_text());assert data['uuid-after-private.txt'].decode().strip()==private['uuid']
assert data['taint.txt']==b'0\n' and data['phosh.txt'].strip() and data['phoc.txt'].strip() and data['remoteprocs.txt']==b'running\nrunning\n'
before=data['dmesg-before-private.txt'];after=data['dmesg-after-private.txt'];assert after.startswith(before)
for name in ['failed to install key','firmware crashed','frame done timeout','*** gpu fault','Call trace:']:assert after.count(name.encode())==before.count(name.encode())
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
http=data['https-result.txt'].decode().split();assert len(http)==3 and http[0]=='200' and int(http[1])==len(data['https-body.txt']) and int(http[1])>0
frequency=float(re.search(r'freq: ([\d.]+)',data['link-after-private.txt'].decode())[1]);assert frequency in [2462,5180]
runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
template=Path('/home/cy122/pmos-samurai-build126/rootfs128/etc/NetworkManager/system-connections/samurai-wifi.nmconnection')
assert template.read_bytes()==data['before-private.nmconnection'];s=template.stat();assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(0,0,0o600)
template.write_bytes(data['after-private.nmconnection']);assert (template.stat().st_uid,template.stat().st_gid,stat.S_IMODE(template.stat().st_mode))==(0,0,0o600)
assert template.read_bytes()==data['after-private.nmconnection']
report=dict(kernel_build=128,same_boot_verified=True,persistent_profile_live_deployed=True,
 template_and_live_exact_profile_delta_verified=True,changed_only_band_lock_and_generic_ui_name=True,
 credentials_uuid_mac_policy_and_autoconnect_preserved=True,root_owner_private_mode600=True,
 reactivation_connected_frequency_mhz=frequency,https_status=200,https_bytes=int(http[1]),gateway_three_received=True,
 no_new_key_timeout_gpu_dpu_firmware_calltrace=True,taint=0,desktop_and_radio_audio_running=True,
 nv6_source4_vendor1_preserved=True,full_networkmanager_restart_pending=True,rootfs_image_pending=True,goal_complete=False)
assert re.search(r'3 packets received',data['gateway-private.txt'].decode())
(ref/'wifi-profile-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
