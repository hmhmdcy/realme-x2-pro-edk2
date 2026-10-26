from pathlib import Path
import hashlib, json, os, subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k200-baseline')
if not out.exists():
    out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#183 ')
assert boot == Path('/var/lib/samurai/k199-baseline/boot-id-private.txt').read_bytes()
if (out / 'boot-id-private.txt').exists():
    assert (out / 'boot-id-private.txt').read_bytes() == boot
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'start-uptime-private.txt').write_text(Path('/proc/uptime').read_text())
assert Path('/sys/firmware/devicetree/base/model').read_bytes() == b'Realme X2 Pro (RMX1931CN)\0'
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '512'
log = subprocess.check_output(['dmesg'])
(out / 'dmesg-private.txt').write_bytes(log)
counts = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
assert counts == dict(warning=3, oops=0, gpu=0, slpi_fatal=0, bluetooth=1)
assert log.count(b'OF: overlay: WARNING: memory leak will occur') == 2
hashes = {}
for device, label, size, digest in [
    ('sde11', 'boot', 100663296, '77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28'),
    ('sde32', 'logdump', 67108864, 'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),
    ('sda2', 'persist', None, '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3')]:
    dev = '/dev/' + device
    assert subprocess.check_output(['lsblk', '-ndo', 'PARTLABEL', dev], text=True).strip() == label
    if size:
        assert int(subprocess.check_output(['blockdev', '--getsize64', dev], text=True)) == size
    actual = subprocess.check_output(['sha256sum', dev], text=True).split()[0]
    assert actual == digest, label
    hashes[label] = actual
(out / 'partitions-private.json').write_text(json.dumps(hashes))
(out / 'partition-check.sha256').write_text(''.join(hashes[label]+'  /dev/'+dev+'\n' for dev,label in [('sde11','boot'),('sde32','logdump'),('sda2','persist')]))
p = subprocess.run(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], capture_output=True, check=True)
(out / 'nv-check-private.txt').write_bytes(p.stdout + p.stderr)
module_root = Path('/usr/lib/modules') / os.uname().release
lines = Path('/var/lib/samurai/k189r2-preflash/old132-module-tree.sha256').read_text().splitlines()
assert len(lines) == 784
(out / 'old132-module-tree.sha256').write_text('\n'.join(lines)+'\n')
for line in lines:
    digest, name = line.split(maxsplit=1)
    name = name.lstrip('*')
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    assert hashlib.sha256((module_root / name).read_bytes()).hexdigest() == digest, name
module = Path(subprocess.check_output(['modinfo', '-n', 'qcom-camss'], text=True).strip())
assert hashlib.sha256(module.read_bytes()).hexdigest() == 'e9b73f4c6bad90fbd6ff89ba45894c88b32b51bc9836ddd741ff56876eb13b0d'
(out / 'camss-original-private.ko').write_bytes(module.read_bytes())
assert (Path('/sys/bus/platform/devices/acb3000.camss') / 'driver').resolve() == Path('/sys/bus/platform/drivers/qcom-camss')
assert Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domain-names').read_bytes() == b'ife0\0ife1\0top\0'
for name in ['samurai_camera_perf','samurai_front_overlay','samurai_vio_phandle','qcom_pm8008','imx471','samurai_cci_bringup','i2c_qcom_cci']:
    assert not Path('/sys/module/' + name).exists()
rp = {(p/'name').read_text().strip(): (p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert all(v == 'running' for v in rp.values())
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest() == 'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
r = dict(stage=200, fresh_current_device_identity_verified=True, kernel_build=183,
    uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), taint=512,
    fault_counts=counts, remoteprocs=rp, original_784_module_tree_files_exact=True,
    old_boot172_and_logdump183_exact=True, persist_and_nv_unchanged=True,
    original_camss_backed_up=True, no_hardware_transition=True)
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
