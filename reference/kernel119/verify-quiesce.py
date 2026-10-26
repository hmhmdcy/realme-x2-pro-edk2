from pathlib import Path
import json,hashlib,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel119');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
p=out/'flash-quiesce-2.tar'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='3eaf50d8bdc1e4a25800432b3f980a7a70357f66f23e3ebef6d2c720aab57c79'
with tarfile.open(p) as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in d['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
assert d['boot-id-private.txt']==(out/'source-boot-id-private.txt').read_bytes()
assert d['state.txt'].splitlines()[-1]==b'0'
assert d['pcm-idle.txt'].strip()==b'closed\nclosed'
assert d['amps-final.txt'].count(b'powered=0 muted=1')==2
assert d['adsp-final-state.txt'].strip()==b'offline'
assert d['soundcards-after-stop.txt'].strip()==b'--- no soundcards ---'
assert d['remoteproc-final-state.txt'].count(b'offline')==3
assert d['sensor-power-final-state.txt'].strip()==b'vdd=0 vddio=0'
assert b'active=0' in d['drm-state-after-gui.txt'] and b'active=1' not in d['drm-state-after-gui.txt']
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
report=dict(quiesce_audit_pass=True,current_kernel=115,target_kernel=118,same_preflash_boot=True,gui_user_and_drm_crtcs_quiesced=True,playback_capture_closed=True,amps_off_muted=True,all_remoteprocs_offline=True,sensor_power_off=True,nv6_source4_vendor_preserved=True,taint=0,archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),freeze_not_yet_performed=True,goal_complete=False)
(ref/'quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'quiesce-validation.json').write_text(json.dumps(dict(report,boot_id=d['boot-id-private.txt'].decode().strip()),indent=2)+'\n')
print(json.dumps(report,indent=2))
