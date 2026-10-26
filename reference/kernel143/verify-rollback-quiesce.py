from pathlib import Path
import tarfile,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel143';out=Path('/mnt/e/edk2-samurai-out/kernel143')
with tarfile.open(out/'rollback-quiesce-private.tar') as tf:
 data={}
 for m in tf:
  assert not m.issym() and not m.islnk()
  if m.isfile():
   name=m.name.removeprefix('./');assert '..' not in Path(name).parts and not Path(name).is_absolute() and name not in data;data[name]=tf.extractfile(m).read()
for line in data['SHA256SUMS'].decode().splitlines():
 digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['boot-id-private.txt'].strip()==(out/'rejected-boot-id-private.txt').read_bytes().strip()
assert len(data['drm-clients-after-gui.txt'].splitlines())==1 and b'active=1' not in data['drm-final-state.txt'] and b'active=0' in data['drm-final-state.txt']
assert data['pcm-idle.txt'].strip()==b'closed\nclosed' and data['amps-final.txt'].count(b'powered=0 muted=1')==2 and b'failed=1' not in data['amps-final.txt']
assert data['soundcards-after-stop.txt'].strip()==b'--- no soundcards ---'
assert data['remoteproc-final-state.txt'].splitlines()==[b'0 slpi offline',b'1 modem offline',b'2 adsp offline'] and data['sensor-power-final-state.txt'].strip()==b'vdd=0 vddio=0'
taint=int(data['state.txt'].splitlines()[-1]);assert taint==0
warning=json.loads(data['known-warning-transition.json'])
assert warning['current_kernel']==143 and warning['target_kernel']==140 and warning['taint']==taint
before=data['dmesg-before.txt'].decode();after=data['dmesg-after.txt'].decode();blank=data['dmesg-at-blank.txt'].decode()
assert after.startswith(before) and after.startswith(blank)
assert before.count('WARNING:')==0 and after.count('WARNING:')==(1 if taint==512 else 0)
delta=after[len(before):]
if taint==512:
    assert delta.count('ida_free called for id=1 which is not allocated.')==1
    assert all(name+'+' in delta for name in ['ida_free','slim_unregister_controller','slim_pd_status','pdr_notifier_work'])
import re
assert not re.search(r'BUG:|Oops:|Kernel panic|Unable to handle kernel|gpu fault:',delta)
assert delta.count('unable to prepare channel')==70
assert delta.count('TX DMA diagnostic: state=3 qmi=1 channel=0 device=0 sg=0 config_sg=0 len=8')==1
assert warning['shutdown_tx_dma_failures']==70 and warning['dma_null_channel_state_down_verified']
assert not re.search(r'frame done timeout|dsi_err_worker',after[len(blank):])
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1),('partition-check.txt',3)]:assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
assert data['new-module-check.txt'].count(b': OK')>=770 and b'FAILED' not in data['new-module-check.txt']
report=dict(quiesce_audit_pass=True,current_kernel=143,target_kernel=140,same_current_boot=True,gui_user_and_drm_crtcs_quiesced=True,no_drm_userspace_clients=True,drm_minor=1,pcm_closed_before_adsp_stop=True,audio_card_absent_after_adsp_stop=True,amps_idle_after_stop=True,all_remoteprocs_offline=True,sensor_power_zero=True,nv6_source4_vendor1_preserved=True,boot_logdump_persist_hashes_still_before=True,same132_module_checks_pass=True,taint=taint,known_shutdown_faults_transition_only=True,shutdown_tx_dma_failures=70,dma_null_channel_state_down_verified=True,old_slimbus_warning_not_fixed=True,clean_runtime_accepted=False,archive_sha256=hashlib.sha256((out/'rollback-quiesce-private.tar').read_bytes()).hexdigest(),goal_complete=False)
(ref/'rollback-quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n');(out/'rollback-quiesce-validation.json').write_text(json.dumps(dict(report,boot_id=data['boot-id-private.txt'].decode().strip()),indent=2)+'\n');print('K143_REJECTED143_ROLLBACK_FULL_QUIESCE_ARCHIVE_GUARD_PASS')
