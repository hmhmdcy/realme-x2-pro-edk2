from pathlib import Path
import json,tarfile,hashlib,re
from datetime import datetime
out=Path('/mnt/e/edk2-samurai-out/kernel119');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
p=out/'current118-health-private.tar.gz'
with tarfile.open(p) as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in d['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
assert d['boot-id-private.txt']==(out/'current-boot-id-private.txt').read_bytes()
dates=re.findall(r'^20\d\d-[^\n]+',d['samples.txt'].decode(),re.M);assert len(dates)==10
assert int(d['finished-epoch.txt'])-int(datetime.fromisoformat(dates[0].replace('Z','+00:00')).timestamp())>=300
assert d['taint.txt'].strip()==b'0' and d['phosh.txt'].strip() and d['phoc.txt'].strip()
assert d['drm-card-name.txt'].strip()==b'card1' and d['connector.txt'].strip()==b'connected'
assert b'phoc' in d['drm-clients.txt']
assert d['pcm.txt'].strip()==b'closed\nclosed' and d['amps.txt'].count(b'powered=0 muted=1')==2
assert d['slpi.txt'].strip()==b'offline' and d['sensor-power.txt'].strip()==b'vdd=0 vddio=0'
assert d['radio-audio.txt'].strip()==b'running\nrunning' and d['traces.txt'].strip()==b'0\n0'
for name,count in [('nv-verify.txt',6),('source-verify.txt',4),('vendor-verify.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
package=json.loads((out.parent/'kernel118/candidate-package-validation.json').read_text())
parts=dict(line.split('  ')[::-1] for line in d['partition-check.sha256'].decode().splitlines())
assert parts['/dev/sde11']==package['boot_115_sha256'] and parts['/dev/sde32']==package['logdump_sha256']
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
before=d['dmesg-before.txt'].decode();after=d['dmesg-after.txt'].decode()
renderer=d['phosh-session-private.txt'].decode().rsplit('GL renderer:',1)[1].splitlines()[0].strip();assert renderer=='FD640'
active_scanout=b'active=1' in d['drm-state.txt']
phoc_buffer=b'allocated by = phoc' in d['drm-state.txt']
modem=json.loads(d['modem-private.json'])['modem']['generic']['state-failed-reason'];assert modem=='sim-missing'
report=dict(kernel_build=118,same_new_boot=True,all_members_verified=True,observation_seconds=300,ten_native_samples_pass=True,phosh_phoc_running=True,drm_physical_card='card1',drm_own_device_path_verified=True,connector_connected=True,phoc_drm_client_present=True,phoc_owns_active_scanout=active_scanout and phoc_buffer,final_crtcs_inactive=not active_scanout,renderer=renderer,taint=0,total_dpu_timeouts=after.count('frame done timeout'),window_dpu_timeouts=after.count('frame done timeout')-before.count('frame done timeout'),gpu_faults=after.count('*** gpu fault'),window_gpu_faults=after.count('*** gpu fault')-before.count('*** gpu fault'),rcu_boot_stalls=after.count('rcu_preempt detected stalls'),ctl_reset_failures=after.count('SW_RESET still pending'),kms_bind_failures=after.count('kms hw init failed'),gmu_reprobe_resource_busy='error -EBUSY: can\'t request region' in after,pcm_closed_amps_idle=True,adsp_mpss_running=True,slpi_offline_sensor_power_off=True,nv6_source4_vendor_persist_gpt18_preserved=True,boot_115_unchanged_logdump_118_exact=True,traces_off=True,wifi_up=d['wlan.txt'].strip()==b'up',zram_active=b'/dev/zram0' in d['swaps.txt'],modem_failure_reason=modem,archive_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),only_one_boot_tested=True,idle_window_only=True,persistent_display_fix_unproven=True,goal_complete=False)
for folder in [out,ref]:(folder/'current-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
