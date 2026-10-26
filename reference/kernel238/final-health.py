"""Current238 scoped health; RGB startup black-frame failure is retained."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import dbus

os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root / 'k236-lab-fix/state-private.json').read_text())['exit_code'] == 0
out = root / 'k238-final-health'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
contexts = ['k238-controlled-rear-r14', 'k238-controlled-rear-r14-r2',
            'k238-controlled-rear-rgb-r14', 'k238-controlled-rear-rgb-r14-r2',
            'k238-vendor-audit', 'k238-vendor-followup']
for name in contexts:
    assert json.loads((root / name / 'state-private.json').read_text())['state'] == 'terminal', name
raw = json.loads((root / 'k238-controlled-rear-r14-r2/summary.json').read_text())
rgb = json.loads((root / 'k238-controlled-rear-rgb-r14-r2/summary.json').read_text())
assert raw['passed'] and len(raw['frames']) == 48
assert not rgb['passed'] and rgb['program_exit'] == 0 and len(rgb['frames']) == 48
assert [f['queued_index'] for f in rgb['frames'] if f['all_zero']] == [1]
for report in [raw, rgb]:
    assert all(report[k] for k in ['all_formats_restored', 'media_graph_restored',
        'sensor_controls_restored', 'rails_unchanged', 'camera_devices_suspended',
        'mclk1_mclk2_disabled', 'trace_instance_removed'])
    assert not report['restore_errors'] and not any(report['fault_delta'].values())
for name in ['k238-vendor-audit', 'k238-vendor-followup']:
    summary = json.loads((root / name / 'summary.json').read_text())
    assert summary['unmounted'] and summary['vendor_before_after_equal']
assert not any('k238' in line for line in Path('/proc/self/mountinfo').read_text().splitlines())
assert not any(p.name.startswith('k238') for p in Path('/sys/kernel/tracing/instances').iterdir())


tree = Path('/usr/lib/modules') / os.uname().release
sha = lambda data: hashlib.sha256(data).hexdigest()
inventory = {str(path.relative_to(tree)): sha(path.read_bytes()) for path in tree.rglob('*') if path.is_file()}
assert inventory == json.loads((root / 'k237-camss-install/module-inventory-after-private.json').read_text())
assert len(inventory) == 789 and sum(name.endswith('.ko') for name in inventory) == 775
def checked(args, name, cwd=None):
    result = subprocess.run(args, capture_output=True, cwd=cwd, timeout=40)
    (out / (name + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, name
checked(['sha256sum', '-c', str(root / 'k236-baseline/userspace-check.sha256')], 'userspace')
checked(['sha256sum', '-c', str(root / 'k235-module-stage/loader-config-after.sha256')], 'loader-config')
assert Path('/lib/apk/db/installed').read_bytes() == (root / 'k236-baseline/installed-before-private.txt').read_bytes()
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
assert not any(p.name.startswith(('k236', 'k238')) for p in Path('/sys/kernel/tracing/instances').iterdir())
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=238, same236_boot_verified=True, default_and_loaded_modules=modules,
              module_ko_count=775, module_related_files=789, packages_userspace_loader_exact=True, partitions_not_rehashed_in_this_scoped_check=True, vendor_readonly_audit_verified_separately=True,
              front_rear_sensors_cci_camss_suspended=True, four_camera_rails_off_users0=True,
              mclk1_mclk2_disabled=True, remoteprocs=remote, sensorproxy_three_has_true=True,
              wifi_connected=True, chrony_normal=True, bluetooth_powered=bluetooth_powered,
              bluetooth_discovering=bluetooth_discovering, bluetooth_connections=bluetooth_connections,
              bluetooth_state_observed_only=True, no_pair_connect_or_disconnect_requested=True,
              gps_enabled=int(loc['Enabled']), gps_refresh_rate=int(loc['GpsRefreshRate']),
              signals_location=bool(loc['SignalsLocation']), gnss_watch_idle_time_prepared=True, gnss_data_workers=0,
              modem_state=int(modem['State']), modem_failed_reason=int(modem['StateFailedReason']),
              modem_power_state=int(modem['PowerState']), user_no_sim=True,
              taint=0, fault_counts=faults, all238_workers_terminal=True, no238_mount_or_trace_left=True, no_scene_pixels_saved=True, rear_raw_48_controlled_frames_passed=True, rear_rgb_48_program_completed=True, rear_rgb_strict_acceptance_failed=True, rear_rgb_zero_queued_index=[1], r14_ram_candidate_not_installed=True, installed_r13_r8_preserved=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
