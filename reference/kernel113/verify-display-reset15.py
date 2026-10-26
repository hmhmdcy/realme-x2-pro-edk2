from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'display-session-reset-boot15.tar'
with tarfile.open(path) as tar:
    data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
with tarfile.open(out/'reboot-audio-clean-15.tar') as tar:
    assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
before=data['dmesg-before.txt'];after=data['dmesg-after.txt'];assert after.startswith(before)
new=after[len(before):]
taint_before=int(data['state-before.txt'].splitlines()[-1])
taint_after=int(data['state-after.txt'].splitlines()[-1])
assert data['slpi-after.txt'].strip()==b'offline' and data['power-after.txt'].strip()==b'vdd=0 vddio=0'
stopped=data['processes-stopped-private.txt'];running=data['processes-after-private.txt']
phoc_stopped=b'/etc/phosh/phoc.ini' not in stopped
phoc_running=b'/etc/phosh/phoc.ini' in running
def active(name):
    states={raw for key,raw in data.items() if key.endswith('-'+name+'-private.txt') and key.startswith('drm-')}
    return sum(len(re.findall(rb'^\s*active=1$',raw,re.M)) for raw in states)
events=[]
for line in new.decode(errors='replace').splitlines():
    if re.search(r'WARNING:|Call trace|drm|dpu|dsi|sofef|\+0x[0-9a-f]+/0x[0-9a-f]+',line,re.I):
        events.append(re.sub(r'\b[0-9a-fA-F]{8,16}\b','<hex>',line))
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),boot_checkpoint='reboot-audio-clean-15',
    phoc_absent_after_greetd_stop=phoc_stopped,phoc_running_after_greetd_start=phoc_running,
    drm_active_crtcs_stopped=active('stopped'),drm_active_crtcs_after=active('after'),
    panel_power_mode_0x9c_logged_after_restart=b'power mode 0x9c' in new,
    dpu_timeouts_before=before.count(b'frame done timeout'),dpu_timeouts_after=after.count(b'frame done timeout'),
    new_dpu_timeouts=new.count(b'frame done timeout'),new_gpu_faults=new.count(b'*** gpu fault'),
    taint_before=taint_before,taint_after=taint_after,kernel_display_events=events,
    reset_health_check_pass=taint_after==0 and b'frame done timeout' not in new and phoc_stopped and phoc_running,
    slpi_offline_and_sensor_power_off=True,physical_recovery_confirmed=False,
    physical_recovery_pending=True,permanent_display_fix_accepted=False,goal_complete=False)
(ref/'display-reset15-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
