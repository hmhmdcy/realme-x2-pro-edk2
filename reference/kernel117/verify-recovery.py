from pathlib import Path
import tarfile,json,hashlib,re
out=Path('/mnt/e/edk2-samurai-out/kernel117');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel117')
def load(name):
    p=out/name
    with tarfile.open(p) as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
    for row in d['SHA256SUMS'].decode().splitlines():
        digest,name=row.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
    return d,hashlib.sha256(p.read_bytes()).hexdigest()
probe,probe_sha=load('panel-reprobe-private.tar.gz')
session,session_sha=load('initial-session-recovery-private.tar.gz')
health,health_sha=load('restored-gui-observation-private.tar.gz')
identity=(out.parent/'kernel115/final-boot-id-private.txt').read_bytes()
for d in [probe,session,health]:assert d['boot-id-private.txt']==identity
assert probe['bind-exit.txt'].strip()==b'0'
assert b'renderD128' in probe['drm.txt'] and b'card0' in probe['drm.txt']
assert probe['panel-driver.txt'].strip().endswith(b'panel-samsung-sofef03f')
assert session['config.sha256'].decode().splitlines()[0].split()[0]==session['config.sha256'].decode().splitlines()[1].split()[0]
assert health['taint.txt'].strip()==b'0'
assert health['phosh.txt'].strip() and health['phoc.txt'].strip()
assert health['connector.txt'].strip()==b'connected'
assert health['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0'
assert health['traces.txt'].strip()==b'0\n0'
for name,count in [('nv-check.txt',6),('source-check.txt',4)]:assert health[name].count(b': OK')==count and b'FAILED' not in health[name]
parts=dict(l.split('  ')[::-1] for l in health['partition-check.sha256'].decode().splitlines())
for node,name in [('/dev/sde11','boot-partition-k115.img'),('/dev/sde32','logdump-k115-ipa-zram.img')]:
    assert parts[node]==hashlib.sha256((out.parent/'kernel115'/name).read_bytes()).hexdigest()
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
before=health['dmesg-before-private.txt'].decode();after=health['dmesg-after-private.txt'].decode()
pcm_closed=health['pcm.txt'].strip()==b'closed\nclosed'
amps_idle=health['amps.txt'].count(b'powered=0')==2 and health['amps.txt'].count(b'muted=1')==2
report=dict(kernel_build=115,same_boot_recovery=True,all_archives_members_verified=True,panel_reprobe_exit=0,
 drm_card_render_restored=True,existing_initial_session_restarted=True,greetd_configuration_unchanged=True,
 phosh_running=True,phoc_running=True,taint=0,connector_connected=True,observation_seconds=45,
 pcm_closed=pcm_closed,amps_idle=amps_idle,slpi_offline_sensor_power_off=True,traces_off=True,nv6_sources4_persist_preserved=True,
 boot_logdump_unchanged=True,no_reboot_or_partition_flash=True,
 total_dpu_timeouts=after.count('frame done timeout'),window_dpu_timeouts=after.count('frame done timeout')-before.count('frame done timeout'),
 gpu_faults=after.count('*** gpu fault'),window_gpu_faults=after.count('*** gpu fault')-before.count('*** gpu fault'),
 gmu_reprobe_resource_busy='error -EBUSY: can\'t request region' in after,
 ipa_register_warnings=after.count('WARNING: drivers/net/ipa/reg.h:87'),
 wifi_up=health['wlan.txt'].strip()==b'up',zram_active=b'/dev/zram0' in health['zram.txt'],
 modem_failure_reason=json.loads(health['modem-private.json'])['modem']['generic']['state-failed-reason'],
 recovery_archive_sha256=probe_sha,session_archive_sha256=session_sha,health_archive_sha256=health_sha,
 persistent_boot_fix=False,long_term_display_stability_accepted=False,goal_complete=False)
for folder in [out,ref]:(folder/'display-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
