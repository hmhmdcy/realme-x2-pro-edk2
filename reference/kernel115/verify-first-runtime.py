from pathlib import Path
import tarfile,hashlib,json,sys
out=Path('/mnt/e/edk2-samurai-out/kernel115')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel115')
sys.path.insert(0,str(ref.parent/'kernel113'))
from inspect_live_fdt import fdt
path=out/'first-runtime.tar'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='27372f9111f80233afba74786b89415ec0f27f9042c582f78801d5617ba29a22'
with tarfile.open(path) as tf:
    data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for row in data['SHA256SUMS'].decode().splitlines():
    digest,name=row.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert b'#115 SMP PREEMPT' in data['uname.txt']
assert data['state.txt'].splitlines()[-1]==b'512'
assert b'/dev/sda16 / f2fs rw' in data['mounts.txt']
assert data['boot-id-private.txt'].decode().strip()!=(out/'source-boot-id-private.txt').read_text().strip()
parts=dict(line.split('  ')[::-1] for line in data['partition-check.sha256'].decode().splitlines())
for node,name in [('/dev/sde11','boot-partition-k115.img'),('/dev/sde32','logdump-k115-ipa-zram.img')]:
    assert parts[node]==hashlib.sha256((out/name).read_bytes()).hexdigest()
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
for name,count in [('nv-check.txt',6),('source-check.txt',4)]:
    assert data[name].count(b': OK')==count and b'FAILED' not in data[name]
expected=fdt((out/'dtb-ipa-zram').read_bytes());live=fdt(data['live-fdt-private.dtb'])
assert expected.keys()==live.keys()
for name,props in expected.items(): assert all(live[name].get(k)==v for k,v in props.items()),name
assert data['power-state.txt'].strip()==b'vdd=0 vddio=0'
log=data['dmesg.txt'].decode()
assert 'IPA driver setup completed successfully' in log
assert 'received modem running event' in log
assert 'rmnet_ipa0' in data['processes.txt'].decode() or 'IPA driver initialized' in log
report=dict(runtime_archive_verified=True,kernel_build=115,boot_logdump_live_dtb_match=True,userdata_f2fs_rw=True,taint=512,nv6_sources4_persist_preserved=True,slpi_offline=True,sensor_power_off=True,ipa_setup_pass=True,modem_running=True,ipa_register_warning_count=log.count('WARNING: drivers/net/ipa/reg.h:87'),dpu_timeouts=log.count('frame done timeout'),gpu_faults=log.count('*** gpu fault'),cellular_data_accepted=False,goal_complete=False)
for dest in [out,ref]: (dest/'first-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
