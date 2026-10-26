from pathlib import Path
import tarfile,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel143';out=Path('/mnt/e/edk2-samurai-out/kernel143')
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
assert data['state.txt'].splitlines()[-1]==b'512'
warning=json.loads(data['known-warning-transition.json'])
assert warning['known_warning_transition_only'] and warning['current_kernel']==140 and warning['target_kernel']==143
assert warning['taint']==512 and warning['warning_count']==1 and warning['old_warning_not_fixed']
before=data['dmesg-before.txt'].decode();after=data['dmesg-after.txt'].decode()
assert after.startswith(before) and before.count('WARNING:')==0 and after.count('WARNING:')==1
delta=after[len(before):]
assert delta.count('ida_free called for id=1 which is not allocated.')==1
assert all(name+'+' in delta for name in ['ida_free','slim_unregister_controller','slim_pd_status','pdr_notifier_work'])
import re
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:|frame done timeout|dsi_err_worker|unable to prepare channel',delta)
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1),('partition-check.txt',3)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['new-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['new-module-check.txt']
report=dict(quiesce_audit_pass=True,current_kernel=140,target_kernel=143,same_current_boot=True,gui_user_and_drm_crtcs_quiesced=True,no_drm_userspace_clients=True,drm_minor=1,pcm_closed_before_adsp_stop=True,audio_card_absent_after_adsp_stop=True,amps_idle_after_stop=True,all_remoteprocs_offline=True,sensor_power_zero=True,nv6_source4_vendor1_preserved=True,boot_logdump_persist_hashes_still_before=True,same132_module_checks_pass=True,taint=512,known_warning_transition_only=True,old_slimbus_warning_not_fixed=True,clean_runtime_accepted=False,archive_sha256=hashlib.sha256((out/'quiesce-private.tar').read_bytes()).hexdigest(),goal_complete=False)
(ref/'quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'quiesce-validation.json').write_text(json.dumps(dict(report,boot_id=data['boot-id-private.txt'].decode().strip()),indent=2)+'\n');print('K143_CURRENT140_FULL_QUIESCE_ARCHIVE_GUARD_PASS')
