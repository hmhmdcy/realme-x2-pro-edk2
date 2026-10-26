from pathlib import Path
import dbus, hashlib, json, os, subprocess
os.umask(0o077)
root = Path('/var/lib/samurai'); out = root / 'k211-before-reboot'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k211-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/sys/firmware/devicetree/base/model').read_bytes() == b'Realme X2 Pro (RMX1931CN)\0'
assert json.loads((root / 'k207-tftp-deploy/summary.json').read_text())['block_fix_installed_and_loaded']
out.mkdir(mode=0o700); (out / 'boot-id-private.txt').write_bytes(boot)
(out / 'start-uptime-private.txt').write_text(Path('/proc/uptime').read_text())
persist = json.loads((root / 'k200-runtime/partition-hashes-private.json').read_text())['persist']
hashes = {}
for dev, label, size, digest in [('sde11', 'boot', 100663296, '89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0'), ('sde32', 'logdump', 67108864, 'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'), ('sda2', 'persist', None, persist)]:
    path = '/dev/' + dev
    assert subprocess.check_output(['lsblk', '-ndo', 'PARTLABEL', path], text=True).strip() == label
    if size: assert int(subprocess.check_output(['blockdev', '--getsize64', path], text=True)) == size
    value = subprocess.check_output(['sha256sum', path], text=True).split()[0]
    assert value == digest, label; hashes[path] = value
(out / 'partition-check.sha256').write_text(''.join(value + '  ' + path + '\n' for path, value in hashes.items()))
subprocess.run(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], check=True, stdout=(out / 'nv-check-private.txt').open('wb'))
tree = (root / 'k211-module-install/module-tree.sha256').read_bytes()
assert len(tree.splitlines()) == 786
(out / 'module-tree.sha256').write_bytes(tree)
subprocess.run(['sha256sum', '-c', str(out / 'module-tree.sha256')], cwd=Path('/usr/lib/modules') / os.uname().release, check=True, stdout=(out / 'module-tree-check-private.txt').open('wb'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected = {'/usr/sbin/samurai-ssc': '9a1fd03f5f8e6f1b893f75465b01d1097419b06d41eaa24438aa1b63ee2f287c', '/usr/bin/ModemManager': 'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc', '/usr/sbin/samurai-gnss-assist': '42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97', '/etc/init.d/samurai-gnss-assist': '54b8174507e97badfafba6c373ebf937045c1c85034f094e7de910369af78af3', '/usr/sbin/samurai-tqftpserv': 'b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1', '/usr/sbin/samurai-wifi': '854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f'}
assert Path('/usr/sbin/samurai-bluetooth').read_bytes() == (root / 'k205-bootdiag-deploy/samurai-bluetooth-original.sh').read_bytes()
expected['/usr/sbin/samurai-bluetooth'] = sha('/usr/sbin/samurai-bluetooth')
expected['/usr/sbin/samurai-modem-configs'] = 'd4c62be6054b3ff74f3ed2868c4b456ccb519f75954ad7094235826559a64862'
expected['/etc/modules-load.d/samurai-camera-heaps.conf']='3dcdfeb7f6c25f12603fa19510a5cbc412b9e4af1c5b5655f89367bbacd27440'
expected['/etc/udev/rules.d/70-samurai-camera-heaps.rules']='edaa592dd125f84da3c59b4d90465a2d1202a8cceda3f0aec5febf31f817f02d'
assert all(sha(name) == digest for name, digest in expected.items())
(out / 'userspace-check.sha256').write_text(''.join(digest + '  ' + name + '\n' for name, digest in expected.items()))
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location'); modem = props.GetAll('org.freedesktop.ModemManager1.Modem')
assert int(loc['Enabled']) == 0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate']) == 30
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
objects = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in objects.values())
adapters = [v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']; bus.close()
watch = json.loads((root / 'gnss-assist/watch-state.json').read_text())
assert watch['running'] and not watch['active'] and watch['worker_starts'] == watch['worker_completions']
assert watch['time_prepared'] and watch['time_preparation_starts'] == watch['time_preparation_completions'] >= 1
rp = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert all(v == 'running' for v in rp.values())
assert json.loads(Path('/run/samurai-ssc/state.json').read_text())['started']
assert Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domain-names').read_bytes() == b'ife0\0ife1\0top\0mmcx\0'
assert all(not Path('/sys/module/' + n).exists() for n in ['samurai_front_overlay', 'samurai_vio_phandle', 'samurai_cci_bringup'])
assert all(Path('/sys/module/' + n).exists() for n in ['imx471', 'qcom_pm8008', 'qcom_pm8008_regulator', 'i2c_qcom_cci', 'v4l2_cci', 'qcom_camss', 'system_heap', 'cma_heap'])
log = subprocess.check_output(['dmesg']); (out / 'dmesg-private.txt').write_bytes(log)
faults = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=211, fresh_current_identity_verified=True, same_current210_baseline_boot=True, taint=0, boot210_logdump183_persist_readback_exact=True, installed_786_file_module_tree_exact=True, new_tftp_and_helper_exact=True, gps_enabled=0, bt_powered=False, bt_connections=0, remoteprocs=rp, fault_counts=faults, no_transition_sent=True, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps(report))
