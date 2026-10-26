"""Current239 r15 default runtime health; optical acceptance stays open."""
from pathlib import Path
import hashlib
import json
import os
import struct
import stat
import subprocess
import dbus

os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root / 'k236-lab-fix/state-private.json').read_text())['exit_code'] == 0
out = root / 'k239-final-health'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
contexts = ['k239-fixed-rgb-r14', 'k239-paired-r14', 'k239-r15-startup',
            'k239-front-r15-raw', 'k239-front-r15-rgb',
            'k239-r15-installed-startup', 'k239-odm-source']
for name in contexts:
    assert json.loads((root / name / 'state-private.json').read_text())['state'] == 'terminal', name
for name in contexts[:-1]:
    report = json.loads((root / name / 'summary.json').read_text())
    assert report['program_exit'] == 0 and not report['worker_exception']
    assert all(report[k] for k in ['all_formats_restored', 'media_graph_restored',
        'sensor_controls_restored', 'rails_unchanged', 'camera_devices_suspended', 'mclk1_mclk2_disabled'])
    assert not report['restore_errors'] and not any(report['fault_delta'].values())
    if 'front' in name:
        assert report['passed'] and len(report['frames']) == 6
    else:
        assert report['diagnostic_capture_completed'] and report['trace_instance_removed']
installed = json.loads((root / 'k239-r15-installed-startup/summary.json').read_text())
assert installed['default_environment_without_candidate_overrides']
assert installed['same_camera_two_start_stop_runs'] and installed['run_count'] == 2
assert len(installed['frames']) == 24 and not installed['strict_nonzero_frames_passed']
assert not installed['passed']  # Retain the independent strict all-nonzero failure.
odm = json.loads((root / 'k239-odm-source/summary.json').read_text())
assert odm['unmounted'] and odm['odm_before_after_equal'] and odm['no_gnss_set_or_search']
transaction = root / 'k239-r15-package-transaction'
assert json.loads((transaction / 'transaction-state-private.json').read_text())['state'] == 'verified'
assert json.loads((transaction / 'policy-reload-state-private.json').read_text())['state'] == 'verified'
policy = json.loads((transaction / 'policy-reload-summary.json').read_text())
assert all(policy[k] for k in ['new_r15_camera_libraries_loaded', 'no_old_deleted_camera_library_mappings',
    'no_candidate_path_environment_overrides', 'pipewire_and_all_desktop_process_identities_unchanged',
    'bluetooth_connected_devices_unchanged', 'no_pair_connect_or_disconnect_requested'])
assert not any('k239' in line for line in Path('/proc/self/mountinfo').read_text().splitlines())
assert not any(p.name.startswith('k239') for p in Path('/sys/kernel/tracing/instances').iterdir())


tree = Path('/usr/lib/modules') / os.uname().release
sha = lambda data: hashlib.sha256(data).hexdigest()
inventory = {str(path.relative_to(tree)): sha(path.read_bytes()) for path in tree.rglob('*') if path.is_file()}
assert inventory == json.loads((root / 'k237-camss-install/module-inventory-after-private.json').read_text())
assert len(inventory) == 789 and sum(name.endswith('.ko') for name in inventory) == 775
def checked(args, name, cwd=None):
    result = subprocess.run(args, capture_output=True, cwd=cwd, timeout=40)
    (out / (name + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, name
manifest = json.loads((root / 'k239-r15-package-candidates/forward-manifest.json').read_text())
names = {p['name'] for p in manifest['packages']}
assert len(names) == 7
expected = {}
for package in manifest['packages']:
    for relative, item in package['files'].items():
        assert relative not in expected
        expected[relative] = item
        path = Path('/') / relative
        if item['kind'] == 'symlink':
            assert path.is_symlink() and os.readlink(path) == item['target']
        else:
            assert path.is_file() and not path.is_symlink()
            assert sha(path.read_bytes()) == item['sha256']
            assert stat.S_IMODE(path.stat().st_mode) == item['mode']
assert len(expected) == 49
def records(data):
    result = {}
    for block in data.decode().split('\n\n'):
        named = [line[2:] for line in block.splitlines() if line.startswith('P:')]
        if named:
            assert len(named) == 1 and named[0] not in result
            result[named[0]] = block
    return result
old = records((transaction / 'installed-before-private.txt').read_bytes())
new = records(Path('/lib/apk/db/installed').read_bytes())
assert len(new) == 944 and set(old) == set(new)
assert all(old[name] == new[name] for name in old if name not in names)
assert all(old[name] != new[name] for name in names)
for package in manifest['packages']:
    assert 'V:' + package['version'] in new[package['name']].splitlines()
retained, replaced = [], []
for line in (root / 'k236-baseline/userspace-check.sha256').read_text().splitlines():
    assert line[64:66] in ['  ', ' *']
    relative = line[66:].lstrip('/')
    if relative in expected:
        replaced.append(relative)
    else:
        retained.append(line)
assert retained and replaced
(out / 'userspace-unmodified-private.sha256').write_text('\n'.join(retained) + '\n')
(out / 'userspace-transaction-paths-private.json').write_text(json.dumps(replaced, indent=2) + '\n')
checked(['sha256sum', '-c', str(out / 'userspace-unmodified-private.sha256')], 'userspace-unmodified')
checked(['sha256sum', '-c', str(root / 'k235-module-stage/loader-config-after.sha256')], 'loader-config')
assert stat.S_IMODE(Path('/etc/libcamera').stat().st_mode) == 0o755
assert not any(Path('/etc/libcamera').glob('*.apk-new'))
config = Path('/etc/libcamera/configuration.yaml').read_text()
assert 'mode: cpu' in config and 'dma_heap: system' in config
assert Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text() == 'ndx file:///var/lib/samurai/k239-r15-package-candidates/forward/packages.adb\n'
wp = []
for proc in Path('/proc').glob('[0-9]*'):
    try:
        if (proc / 'comm').read_text().strip() == 'wireplumber':
            wp.append(proc)
    except OSError:
        pass
assert len(wp) == 1
maps = (wp[0] / 'maps').read_text()
camera_lines = [line for line in maps.splitlines() if '/usr/lib/libcamera' in line]
assert camera_lines and all('(deleted)' not in line for line in camera_lines)
assert any('/usr/lib/libcamera.so.' in line for line in camera_lines)
for line in camera_lines:
    path = line.split()[-1]
    assert sha(Path(path).read_bytes()) == expected[path.lstrip('/')]['sha256']
def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    found = [data[s[4]:s[4]+s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(found) == 1
    return found[0]
modules = {}
for name, relative in [('qcom_pm8008', 'kernel/drivers/mfd/qcom-pm8008.ko'),
                        ('qcom_pm8008_imx319_lab', 'kernel/drivers/regulator/qcom-pm8008-imx319-lab.ko'),
                        ('reset_realme_rmx1931_pm8008', 'kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko'),
                        ('imx319', 'kernel/drivers/media/i2c/imx319.ko'), ('imx471', 'kernel/drivers/media/i2c/imx471.ko'),
                        ('qcom_camss', 'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'),
                        ('fastrpc', 'kernel/drivers/misc/fastrpc.ko'), ('hci_uart', 'kernel/drivers/bluetooth/hci_uart.ko')]:
    data = (tree / relative).read_bytes()
    assert Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes() == note(data)
    modules[name] = sha(data)
for node in ['/sys/bus/i2c/devices/7-0010', '/sys/bus/i2c/devices/9-0010',
             '/sys/bus/platform/devices/ac4a000.cci', '/sys/bus/platform/devices/ac4b000.cci',
             '/sys/bus/platform/devices/acb3000.camss']:
    assert Path(node, 'power/runtime_status').read_text().strip() == 'suspended', node
rails = {}
for node in Path('/sys/class/regulator').glob('regulator.*'):
    name = (node / 'name').read_text().strip()
    if not name.startswith(('cam-front-', 'cam-rear-')):
        continue
    rails[name] = {field: (node / field).read_text().strip() for field in ['state', 'num_users', 'microvolts']}
    assert rails[name]['state'] == 'disabled' and rails[name]['num_users'] == '0'
assert set(rails) == {'cam-front-vana', 'cam-front-vdig', 'cam-rear-vana', 'cam-rear-vdig'}
clocks = Path('/sys/kernel/debug/clk/clk_summary').read_text()
for name in ['cam_cc_mclk1_clk', 'cam_cc_mclk2_clk']:
    rows = [line.split() for line in clocks.splitlines() if line.split() and line.split()[0] == name]
    assert len(rows) == 1 and int(rows[0][1]) == 0
remote = {(node / 'name').read_text().strip(): (node / 'state').read_text().strip() for node in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == dict(adsp='running', slpi='running', modem='running')
bus = dbus.SystemBus(private=True)
sensor = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties')
assert all(sensor.Get('net.hadess.SensorProxy', name) for name in ['HasAccelerometer', 'HasAmbientLight', 'HasProximity'])
blue = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters = [value['org.bluez.Adapter1'] for value in blue.values() if 'org.bluez.Adapter1' in value]
assert len(adapters) == 1
# Observe external state. This checker sends no pairing/connect/disconnect calls.
bluetooth_powered = bool(adapters[0]['Powered'])
bluetooth_discovering = bool(adapters[0]['Discovering'])
bluetooth_connections = sum(bool(value.get('org.bluez.Device1', {}).get('Connected', False)) for value in blue.values())
mm = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
paths = [path for path, value in mm.items() if 'org.freedesktop.ModemManager1.Modem' in value]
assert len(paths) == 1
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', paths[0]), 'org.freedesktop.DBus.Properties')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
modem = props.GetAll('org.freedesktop.ModemManager1.Modem')
assert int(loc['Enabled']) == 0
watch = json.loads((root / 'gnss-assist/watch-state.json').read_text())
assert watch['running'] and not watch['active'] and watch['time_prepared']
assert watch['worker_starts'] == watch['worker_completions'] == 0
nm = dbus.Interface(bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager'), 'org.freedesktop.NetworkManager')
wifi = []
for path in nm.GetDevices():
    props = dbus.Interface(bus.get_object('org.freedesktop.NetworkManager', path), 'org.freedesktop.DBus.Properties')
    if str(props.Get('org.freedesktop.NetworkManager.Device', 'Interface')) == 'wlan0':
        wifi.append(int(props.Get('org.freedesktop.NetworkManager.Device', 'State')))
assert wifi == [100]
bus.close()
chrony = subprocess.check_output(['chronyc', 'tracking'], text=True, timeout=10)
(out / 'chrony-private.txt').write_text(chrony)
assert 'Normal' in chrony
log = subprocess.check_output(['dmesg'])
(out / 'dmesg-private.txt').write_bytes(log)
faults = {name: log.count(needle) for name, needle in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:',
    dsp_fatal=b'fatal error received', bt_reassembly=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert not any(path.read_text().strip() for path in Path('/sys/module').glob('*/taint'))
assert not any(p.name.startswith(('k236', 'k238', 'k239')) for p in Path('/sys/kernel/tracing/instances').iterdir())
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=239, same236_boot_verified=True, default_and_loaded_modules=modules,
              module_ko_count=775, module_related_files=789, packages_userspace_loader_exact_except_verified_seven_package_upgrade=True, installed_r15_r10=True, installed_payload_records=49, package_count=944, unrelated_package_records_unchanged=937, default_runtime_two_start_diagnostic_and_policy_reload_verified=True, partitions_not_rehashed_in_this_scoped_check=True, vendor_readonly_audit_verified_separately=True,
              front_rear_sensors_cci_camss_suspended=True, four_camera_rails_off_users0=True,
              mclk1_mclk2_disabled=True, remoteprocs=remote, sensorproxy_three_has_true=True,
              wifi_connected=True, chrony_normal=True, bluetooth_powered=bluetooth_powered,
              bluetooth_discovering=bluetooth_discovering, bluetooth_connections=bluetooth_connections,
              bluetooth_state_observed_only=True, no_pair_connect_or_disconnect_requested=True,
              gps_enabled=int(loc['Enabled']), gps_refresh_rate=int(loc['GpsRefreshRate']),
              signals_location=bool(loc['SignalsLocation']), gnss_watch_idle_time_prepared=True, gnss_data_workers=0,
              modem_state=int(modem['State']), modem_failed_reason=int(modem['StateFailedReason']),
              modem_power_state=int(modem['PowerState']), user_no_sim=True,
              taint=0, fault_counts=faults, all239_workers_terminal=True, no239_mount_or_trace_left=True, no_scene_pixels_saved=True, paired_raw_rgb_twelve_requests_complete=True, front_raw_rgb_six_each_passed=True, installed_rear_rgb_two_starts_24_frames_complete=True, rear_rgb_strict_acceptance_failed=True, scene_optical_response_and_colour_open=True, old_r13_r8_rollback_payloads_preserved=True, no_new_gnss_search_or_set=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
