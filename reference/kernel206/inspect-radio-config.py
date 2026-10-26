"""Read-only firmware-service/PDC discovery; no GPS start or config activation."""
from pathlib import Path
import dbus, hashlib, json, os, re, shutil, subprocess

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k206-radio-inspection'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k205r2-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root / 'k206-bt-restore/summary.json').read_text())['restored185_module_and_loaded_build_id']
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
modem = props.GetAll('org.freedesktop.ModemManager1.Modem')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled']) == 0
before_mm_owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
processes = []
for p in Path('/proc').glob('[0-9]*'):
    try:
        args = (p / 'cmdline').read_bytes().split(b'\0')
        if any(re.search(rb'rmtfs|tqftp|qrtr|qmi-proxy|ModemManager|cnss|samurai-wifi|gnss-assist', a) for a in args):
            processes.append(dict(pid=int(p.name), args=[a.decode(errors='replace') for a in args if a]))
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        pass
(out / 'service-processes-private.json').write_text(json.dumps(processes, indent=2) + '\n')
files = []
for name in ['/usr/sbin/samurai-wifi', '/usr/sbin/samurai-firmware', '/etc/init.d/samurai-wifi', '/etc/init.d/modemmanager']:
    p = Path(name)
    if p.is_file():
        files.append(name)
        shutil.copyfile(p, out / (name.strip('/').replace('/', '__') + '-private'))
for base in ['/run/samurai-wifi', '/var/lib/samurai/firmware', '/var/lib/rmtfs', '/var/lib/tftpboot']:
    p = Path(base)
    if p.is_dir():
        (out / (base.strip('/').replace('/', '__') + '-files-private.json')).write_text(json.dumps([str(q) for q in p.rglob('*')][:1500], indent=2) + '\n')
        if base == '/run/samurai-wifi':
            for q in p.iterdir():
                if q.is_file() and q.stat().st_size <= 2_000_000 and (q.suffix == '.log' or 'log' in q.name):
                    shutil.copyfile(q, out / (q.name + '-private'))

def command(args, label, timeout=35):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (label + '-private.log')).write_bytes(p.stdout + p.stderr)
    return p
help_result = command(['qmicli', '--help-pdc'], 'qmicli-pdc-help')
assert help_result.returncode == 0
assert b'--pdc-get-selected-config=' in help_result.stdout and b'--pdc-list-configs=' in help_result.stdout
results = {}
for action, label in [('--pdc-get-selected-config=software', 'pdc-selected-software'), ('--pdc-list-configs=software', 'pdc-list-software')]:
    p = command(['qmicli', '-d', 'qrtr://0', '--device-open-proxy', action], label)
    results[label] = dict(exit=p.returncode, bytes=len(p.stdout) + len(p.stderr))
assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == before_mm_owner
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
bus.close()
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
result = dict(stage=206, same_r2_boot_verified=True, read_only_queries=True, pdc_requests=results, configuration_selected_or_activated=False, gps_session_started=False, modem_restarted=False, modem_owner_unchanged=True, service_processes=len(processes), startup_scripts_captured=len(files), modem_power_state=int(modem['PowerState']), modem_state=int(modem['State']), modem_failed_reason=int(modem['StateFailedReason']), taint=int(Path('/proc/sys/kernel/tainted').read_text()), uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
