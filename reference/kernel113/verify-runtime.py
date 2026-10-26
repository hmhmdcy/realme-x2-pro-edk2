from pathlib import Path
import hashlib,json,re,tarfile,sys
from inspect_live_fdt import fdt

out = Path('/mnt/e/edk2-samurai-out/kernel113')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
prefix = sys.argv[1]; assert re.fullmatch('[a-z0-9-]+',prefix)
path = out/(prefix+'.tar'); sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tarfile.open(path) as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert b'#113 SMP PREEMPT' in data['uname.txt']
assert data['state.txt'].splitlines()[-1]==b'0'
assert b'/dev/sda16 / f2fs rw' in data['mounts.txt']
assert data['nv-check.txt'].count(b': OK')==6 and data['source-check.txt'].count(b': OK')==4
parts=dict(line.split('  ')[::-1] for line in data['partition-check.sha256'].decode().splitlines())
for dev,name in [('/dev/sde11','boot-partition-k113.img'),('/dev/sde32','logdump-k113-sensor-power.img')]:
    assert parts[dev]==sha(out/name)
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
expected=fdt((out/'dtb-sensor-power').read_bytes())
live=fdt(data['live-fdt-private.dtb'])
assert expected.keys()==live.keys()
efi={'linux,uefi-system-table','linux,uefi-mmap-start','linux,uefi-mmap-size',
     'linux,uefi-mmap-desc-size','linux,uefi-mmap-desc-ver'}
for name,props in expected.items():
    assert all(live[name].get(key)==value for key,value in props.items()),name
    assert set(live[name])-set(props) <= (efi if name=='/chosen' else set()),name
assert data['power-state.txt'].strip()==b'vdd=0 vddio=0'
assert data['boot-id-private.txt'].decode().strip()!=(out/'source-boot-id-private.txt').read_text().strip()
log=data['dmesg.txt'].decode(errors='replace')
assert re.search(r'\[\s*0\.000000\]',log) and 'stock sensor supplies ready; manual activation required' in log
assert b'slpi\noffline\n' in data['remoteprocs.txt']
report=dict(runtime_audit_pass=True,kernel_build=113,archive_sha256=sha(path),
            taint=0,full_early_log_present=True,userdata_f2fs_rw=True,
            boot_logdump_and_live_dtb_match=True,nv6_sources4_persist_unchanged=True,
            slpi_auto_boot=False,sensor_power_default_off=True,
            dpu_timeouts=log.count('frame done timeout'),gpu_faults=log.count('*** gpu fault'),
            sensor_function_accepted=False,goal_complete=False)
(out/(prefix+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
(ref/(prefix+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
