"""First post-reboot observation: no manual GPS time/data or RF power change."""
from pathlib import Path
import dbus, hashlib, json, os, struct, subprocess

os.umask(0o077)
root = Path('/var/lib/samurai')
before = root/'k202-before-reboot'
out = root/'k202-runtime'
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot != (before/'boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes() == b'Realme X2 Pro (RMX1931CN)\0'
if out.exists():
    assert (out/'boot-id-private.txt').read_bytes() == boot
else:
    out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
for name in ['partition', 'userspace']:
    subprocess.run(['sha256sum', '-c', str(before/(name+'-check.sha256'))], check=True, stdout=(out/(name+'-check-private.txt')).open('wb'))
subprocess.run(['sha256sum', '-c', str(before/'module-tree.sha256')], cwd=Path('/usr/lib/modules')/os.uname().release, check=True, stdout=(out/'module-tree-check-private.txt').open('wb'))
subprocess.run(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], check=True, stdout=(out/'nv-check-private.txt').open('wb'))
quiesce = json.loads((root/'k202-quiesce/quiesce-validation.json').read_text())
assert quiesce['stage'] == 202 and quiesce['taint'] == 0 and quiesce['quiesce_audit_pass']
watch = json.loads((root/'gnss-assist/watch-state.json').read_text())
if not (out/'watch-first-private.json').exists():
    (out/'watch-first-private.json').write_text(json.dumps(watch, indent=2)+'\n')
(out/'watch-current-private.json').write_text(json.dumps(watch, indent=2)+'\n')
assert watch['running'] and not watch['active'] and watch['worker_starts'] == watch['worker_completions'] == 0
pid = int(Path('/run/samurai-gnss-assist.pid').read_text())
args = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')
assert b'/usr/sbin/samurai-gnss-assist' in args and b'--watch' in args
assert Path('/etc/runlevels/default/samurai-gnss-assist').resolve() == Path('/etc/init.d/samurai-gnss-assist')
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
modem = props.GetAll('org.freedesktop.ModemManager1.Modem')
assert int(loc['Enabled']) == 0
geo = bus.name_has_owner('org.freedesktop.GeoClue2')
bus.close()
dt = Path('/sys/firmware/devicetree/base')
assert (dt/'soc@0/camss@acb3000/power-domain-names').read_bytes() == b'ife0\0ife1\0top\0mmcx\0'
log = subprocess.check_output(['dmesg'])
(out/'dmesg-private.txt').write_bytes(log)
counts = {k: log.count(v) for k,v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
rp = {(p/'name').read_text().strip(): (p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
chrony = subprocess.run(['chronyc', 'tracking'], capture_output=True, text=True, timeout=10)
(out/'chrony-first-private.txt').write_text(chrony.stdout+chrony.stderr)
report = dict(stage=202, new_boot_identity_verified=True, kernel_build=183, taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    unchanged_boot200_logdump183_persist_and_nv=True, module_tree_784_files_exact=True, helper_and_mm191_exact=True,
    previous_boot_full_quiesce_verified=True, partitions_flashed=[],
    gnss_service_autostarted=True, gnss_service_idle=True, worker_starts=watch['worker_starts'],
    worker_completions=watch['worker_completions'], manual_time_or_assistance_injection=False,
    modem_power_state=int(modem['PowerState']), modem_state=int(modem['State']), failed_reason=int(modem['StateFailedReason']),
    gps_enabled=int(loc['Enabled']), signals_location=bool(loc['SignalsLocation']), gps_refresh_rate=int(loc['GpsRefreshRate']),
    geoclue_bus_owned=geo, chrony_normal=chrony.returncode == 0 and 'Normal' in chrony.stdout,
    remoteprocs=rp, camss_loaded_automatically=Path('/sys/module/qcom_camss').exists(),
    camss_platform_bound=Path('/sys/bus/platform/devices/acb3000.camss/driver').exists(),
    uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), fault_counts=counts)
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
