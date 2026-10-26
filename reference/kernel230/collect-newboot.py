"""Observe automatic boot/readiness with the new module, without starting GNSS."""
from pathlib import Path
import dbus
import hashlib
import json
import os
import struct
import subprocess
import time
import traceback

os.umask(0o077)
root = Path('/var/lib/samurai')
before = root / 'k230-baseline'
out = root / 'k230-runtime'
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot != (before / 'boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes() == b'Realme X2 Pro (RMX1931CN)\0'
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
state = dict(state='running', pid=os.getpid(), start_ticks=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])


def save():
    temp = out / 'state-new-private.json'
    temp.write_text(json.dumps(state, indent=2) + '\n')
    os.replace(temp, out / 'state-private.json')


def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    found = [data[s[4]:s[4] + s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(found) == 1
    return found[0]


def checked(args, label, cwd=None):
    result = subprocess.run(args, capture_output=True, cwd=cwd, timeout=35)
    (out / (label + '-private.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, label


save()
try:
    log = subprocess.check_output(['dmesg'])
    (out / 'dmesg-first-private.txt').write_bytes(log)
    checked(['sha256sum', '-c', str(before / 'partition-check.sha256')], 'partitions')
    checked(['sha256sum', '-c', str(before / 'userspace-check.sha256')], 'userspace')
    checked(['sha256sum', '-c', str(before / 'module-tree.sha256')], 'module-tree', Path('/usr/lib/modules') / os.uname().release)
    assert Path('/lib/apk/db/installed').read_bytes() == (before / 'installed-before-private.txt').read_bytes()
    deadline = time.monotonic() + 180
    observations = []
    bus = dbus.SystemBus(private=True)
    while True:
        rp = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
        ssc_path = Path('/run/samurai-ssc/state.json')
        ssc = json.loads(ssc_path.read_text()) if ssc_path.exists() else {}
        watch_path = root / 'gnss-assist/watch-state.json'
        watch = json.loads(watch_path.read_text()) if watch_path.exists() else {}
        sensor_has = {}
        if bus.name_has_owner('net.hadess.SensorProxy'):
            props = dbus.Interface(bus.get_object('net.hadess.SensorProxy', '/net/hadess/SensorProxy'), 'org.freedesktop.DBus.Properties')
            sensor_has = {n: bool(props.Get('net.hadess.SensorProxy', n)) for n in ['HasAccelerometer', 'HasAmbientLight', 'HasProximity']}
        observation = dict(remoteprocs=rp, ssc_started=bool(ssc.get('started')), sensor_proxy=sensor_has,
                           watch_running=bool(watch.get('running')), utc_prepared=bool(watch.get('time_prepared')),
                           module_loaded=Path('/sys/module/fastrpc').exists())
        observations.append(observation)
        state['latest_observation'] = observation
        save()
        (out / 'readiness-observations-private.json').write_text(json.dumps(observations, indent=2) + '\n')
        if (rp == dict(adsp='running', slpi='running', modem='running') and ssc.get('started') and
                len(sensor_has) == 3 and all(sensor_has.values()) and watch.get('running') and watch.get('time_prepared')):
            break
        assert time.monotonic() < deadline, 'Automatic startup/readiness timeout; preserve this attempt'
        time.sleep(2)
    module = Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/misc/fastrpc.ko'
    assert hashlib.sha256(module.read_bytes()).hexdigest() == '2abde0ead81c2feb78f639da2ab29d7c3e29654a9d013a098418b232a5cfd794'
    assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes() == note(module.read_bytes())
    assert subprocess.check_output(['modinfo','-F','intree',str(module)],text=True).strip()=='Y'
    assert not any(p.read_text().strip() for p in Path('/sys/module').glob('*/taint'))
    (out / 'ssc-state-private.json').write_text(json.dumps(ssc, indent=2) + '\n')
    checked(['rc-service', 'samurai-ssc', 'status'], 'ssc-status')
    readiness = {}
    for name, label in [('accelerometer', 'Accelerometer'), ('light', 'Light')]:
        data = (Path('/run/samurai-ssc') / (name + '-readiness-private.log')).read_bytes()
        (out / (name + '-automatic-readiness-private.log')).write_bytes(data)
        text = data.decode(errors='replace')
        count = text.count(label + ' sensor measurement:')
        disabled = (label + ' sensor disabled').lower() in text.lower()
        assert count > 0 and disabled
        readiness[name] = dict(measurements=count, clean_disable=True)
    refcount = int(Path('/sys/module/fastrpc/refcnt').read_text())
    assert refcount >= 1, 'Live sensor daemon must pin the new module'
    checked(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv')
    assert watch['running'] and not watch['active'] and watch['worker_starts'] == watch['worker_completions'] == 0
    assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip() == 'N'
    # Compare both camera modules' loaded notes against the retained rootfs files.
    for name, path in [('imx471', 'kernel/drivers/media/i2c/imx471.ko'),
                       ('qcom_camss', 'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko')]:
        data = (Path('/usr/lib/modules') / os.uname().release / path).read_bytes()
        assert Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes() == note(data)
    mm = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    paths = [p for p, v in mm.items() if 'org.freedesktop.ModemManager1.Modem' in v]
    assert len(paths) == 1
    props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', paths[0]), 'org.freedesktop.DBus.Properties')
    loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
    modem = props.GetAll('org.freedesktop.ModemManager1.Modem')
    assert int(loc['Enabled']) == 0
    blue = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
    adapters = [v['org.bluez.Adapter1'] for v in blue.values() if 'org.bluez.Adapter1' in v]
    assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
    assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in blue.values())
    bus.close()
    log = subprocess.check_output(['dmesg'])
    (out / 'dmesg-ready-private.txt').write_bytes(log)
    faults = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
    assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
    report = dict(stage=230, new_boot_identity_verified=True, kernel_build=183, candidate_loaded_note_verified=True,
                  fastrpc_module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(), module_refcount=refcount,
                  boot219_logdump183_persist_nv_exact=True, module_tree786_exact=True, packages_and_helpers_unchanged=True,
                  camera_e49_fae1_loaded_notes_match=True, framework_r13_config_r8_preserved=True,
                  ssc_automatic_start_real_readiness=True, automatic_readiness=readiness, sensor_proxy=sensor_has,
                  remoteprocs=rp, taint=0, faults=faults, gps_enabled=int(loc['Enabled']), signals_location=bool(loc['SignalsLocation']),
                  gps_refresh_rate=int(loc['GpsRefreshRate']), modem_state=int(modem['State']), modem_power_state=int(modem['PowerState']),
                  modem_failed_reason=int(modem['StateFailedReason']), user_no_sim=True,
                  gnss_utc_prepared_automatically=True, gnss_data_workers=0, manual_gnss_session_or_aiding=False,
                  bt_powered=False, bt_connections=0, partitions_flashed=[], uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
    (out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    state.update(state='terminal', exit_code=0)
    save()
except BaseException:
    (out / 'failure-private.txt').write_text(traceback.format_exc())
    state.update(state='terminal', exit_code=1)
    save()
    raise
