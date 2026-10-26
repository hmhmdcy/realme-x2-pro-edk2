from pathlib import Path
import tarfile,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel142';out=Path('/mnt/e/edk2-samurai-out/kernel142')
with tarfile.open(out/'quiesce-private.tar') as tf:
 data={}
 for m in tf:
  assert not m.issym() and not m.islnk()
  if m.isfile():
   name=m.name.removeprefix('./');assert '..' not in Path(name).parts and not Path(name).is_absolute() and name not in data;data[name]=tf.extractfile(m).read()
for line in data['SHA256SUMS'].decode().splitlines():
 digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['boot-id-private.txt'].strip()==(out/'source-boot-id-private.txt').read_bytes().strip()
assert len(data['drm-clients-after-gui.txt'].splitlines())==1 and b'active=1' not in data['drm-final-state.txt'] and b'active=0' in data['drm-final-state.txt']
assert data['pcm-idle.txt'].strip()==b'closed\nclosed' and data['amps-final.txt'].count(b'powered=0 muted=1')==2 and b'failed=1' not in data['amps-final.txt']
assert data['soundcards-after-stop.txt'].strip()==b'--- no soundcards ---'
assert data['remoteproc-final-state.txt'].splitlines()==[b'0 slpi offline',b'1 modem offline',b'2 adsp offline'] and data['sensor-power-final-state.txt'].strip()==b'vdd=0 vddio=0'
assert data['state.txt'].splitlines()[-1]==b'0'
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1),('partition-check.txt',3)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['new-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['new-module-check.txt']
report=dict(quiesce_audit_pass=True,current_kernel=140,target_kernel=140,same_current_boot=True,gui_user_and_drm_crtcs_quiesced=True,no_drm_userspace_clients=True,drm_minor=1,pcm_closed_before_adsp_stop=True,audio_card_absent_after_adsp_stop=True,amps_idle_after_stop=True,all_remoteprocs_offline=True,sensor_power_zero=True,nv6_source4_vendor1_preserved=True,boot_logdump_persist_hashes_still_before=True,same132_module_checks_pass=True,taint=0,archive_sha256=hashlib.sha256((out/'quiesce-private.tar').read_bytes()).hexdigest(),goal_complete=False)
(ref/'quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'quiesce-validation.json').write_text(json.dumps(dict(report,boot_id=data['boot-id-private.txt'].decode().strip()),indent=2)+'\n');print('K142_CURRENT140_FULL_QUIESCE_ARCHIVE_GUARD_PASS')
