from pathlib import Path
import hashlib,json,sys,tarfile,re
out=Path('/mnt/e/edk2-samurai-out/kernel115')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
sys.path.insert(0,str(ref.parent/'kernel113'))
from inspect_live_fdt import fdt
archive=out/'final-health-private.tar.gz'
with tarfile.open(archive) as tf:
    data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for row in data['SHA256SUMS'].decode().splitlines():
    digest,name=row.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest,name
assert b'#115 SMP PREEMPT' in data['uname.txt']
assert data['boot-id-private.txt'].decode().strip()!=(out/'recover-source-boot-id-private.txt').read_text().strip()
assert b'/dev/sda16 / f2fs rw' in data['mounts.txt']
parts=dict(line.split('  ')[::-1] for line in data['partition-check.sha256'].decode().splitlines())
for node,name in [('/dev/sde11','boot-partition-k115.img'),('/dev/sde32','logdump-k115-ipa-zram.img')]:
    assert parts[node]==hashlib.sha256((out/name).read_bytes()).hexdigest()
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
for name,count in [('nv-check.txt',6),('source-check.txt',4)]:
    assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
expected=fdt((out/'dtb-ipa-zram').read_bytes());live=fdt(data['live-fdt-private.dtb'])
assert expected.keys()==live.keys()
for name,props in expected.items(): assert all(live[name].get(k)==v for k,v in props.items()),name
assert data['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0'
assert data['ipa-module.sha256'].decode().split()[0]=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
assert data['pcm.txt'].strip()==b'closed\nclosed'
assert data['amps.txt'].count(b'powered=0')==2 and data['amps.txt'].count(b'muted=1')==2
boot_traces_off=all(line.split()[-1]=='0' for line in data.get('traces.txt',b'').decode().splitlines())
log=data['dmesg.txt'].decode()
assert 'IPA driver setup completed successfully' in log
modem=json.loads(data['modem-private.json'])['modem']
report=dict(runtime_archive_verified=True,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),kernel_build=115,
 boot_logdump_live_dtb_match=True,userdata_f2fs_rw=True,taint=int(data['state.txt'].splitlines()[-1]),
 nv6_sources4_persist_preserved=True,slpi_offline=True,sensor_power_off=True,pcm_closed_amps_idle=True,traces_off_at_capture=boot_traces_off,
 ipa_setup_pass=True,ipa_register_warning_count=log.count('WARNING: drivers/net/ipa/reg.h:87'),fixed_ipa_module=True,
 modemmanager_detects_modem=True,modem_state=modem['generic']['state'],modem_failure_reason=modem['generic']['state-failed-reason'],
 zram_active=b'/dev/zram0' in data['zram.txt'],wifi_up=data['wlan-state.txt'].strip()==b'up',
 phosh_running=bool(data['phosh.txt'].strip()),phoc_running=bool(data['phoc.txt'].strip()),
 display_kms_bind_failed='kms hw init failed: -22' in log or 'kms_init failed' in log,
 rcu_stalls=len(re.findall('rcu: INFO: rcu_preempt detected stalls',log)),
 dpu_frame_timeouts=log.count('frame done timeout'),gpu_faults=log.count('*** gpu fault'),
 graphics_counts_not_acceptance=True,cellular_data_accepted=False,goal_complete=False)
(out/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(ref/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'final-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
(out/'final-dmesg-private.txt').write_bytes(data['dmesg.txt'])
print(json.dumps(report,indent=2))
