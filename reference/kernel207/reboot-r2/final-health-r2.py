from pathlib import Path
import dbus, hashlib, json, os, runpy, subprocess
os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k207r2-final-health-r2'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207r2-runtime/boot-id-private.txt').read_bytes()
test = json.loads((root / 'k207r2-geoclue-first-session/summary.json').read_text())
assert test['client_exit'] == 0 and test['test_config_and_identity_removed'] and test['desktop_location_setting_restored']
assert test['automatic_worker_starts'] == test['automatic_worker_completions'] == 1
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled']) == 0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
late = dict(signals_location=bool(loc['SignalsLocation']), gps_refresh_rate=int(loc['GpsRefreshRate']))
(out / 'idle-location-before-private.json').write_text(json.dumps(late, indent=2) + '\n')
normalized = False
if late != dict(signals_location=False, gps_refresh_rate=30):
    api = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.ModemManager1.Modem.Location')
    api.Setup(dbus.UInt32(0), dbus.Boolean(False), timeout=25)
    api.SetGpsRefreshRate(dbus.UInt32(30), timeout=10)
    normalized = True
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert not loc['SignalsLocation'] and int(loc['GpsRefreshRate']) == 30
modem = props.GetAll('org.freedesktop.ModemManager1.Modem')
bt = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters = [v['org.bluez.Adapter1'] for v in bt.values() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in bt.values())
bus.close()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('/usr/bin/ModemManager') == 'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
assert sha('/usr/sbin/samurai-gnss-assist') == '42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97'
assert sha('/usr/sbin/samurai-tqftpserv') == 'b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1'
assert sha('/usr/sbin/samurai-wifi') == '854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f'
assert Path('/usr/sbin/samurai-bluetooth').read_bytes() == (root / 'k205-bootdiag-deploy/samurai-bluetooth-original.sh').read_bytes()
assert Path('/etc/bluetooth/main.conf').read_bytes() == (root / 'k205-bt-policy/main.conf-before-private').read_bytes()
assert sha(Path('/usr/lib/modules') / os.uname().release / 'kernel/drivers/bluetooth/hci_uart.ko') == 'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
pid = int(Path('/run/samurai-wifi/tftp.pid').read_text())
assert sha('/proc/%d/exe' % pid) == sha('/usr/sbin/samurai-tqftpserv')
watch = json.loads((root / 'gnss-assist/watch-state.json').read_text())
assert watch['running'] and not watch['active'] and watch['worker_starts'] == watch['worker_completions'] == 1
watch_snapshot = out / 'watch-private.json'; watch_snapshot.write_text(json.dumps(watch, indent=2) + '\n')
namespace = runpy.run_path('/usr/sbin/samurai-gnss-assist', run_name='final_readonly')
validity = namespace['loc_exchange']('validity')
(out / 'validity-private.json').write_text(json.dumps(validity, indent=2) + '\n')
assert namespace['validity_current'](validity['start'], validity['hours'], __import__('time').time())
check = subprocess.run(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], capture_output=True)
(out / 'nv-source-check-private.txt').write_bytes(check.stdout + check.stderr); assert check.returncode == 0
mounts = subprocess.check_output(['findmnt', '-J', '-T', '/run/samurai-wifi/tftp-rw', '-o', 'FSTYPE,OPTIONS'])
(out / 'cache-mount-private.json').write_bytes(mounts)
mount = json.loads(mounts)['filesystems'][0]
assert mount['fstype'] == 'tmpfs' and 'size=32768k' in mount['options']
assert not Path('/run/samurai-wifi/tftp-rw/samurai-validation206').exists()
for p in ['/etc/geoclue/conf.d/99-samurai-gnss-test.conf', '/usr/share/applications/org.realme.SamuraiGNSSValidation.desktop', '/usr/libexec/samurai-gnss-validation']:
    assert not Path(p).exists()
assert sha('/usr/sbin/samurai-modem-configs')=='d4c62be6054b3ff74f3ed2868c4b456ccb519f75954ad7094235826559a64862'
manifest=json.loads(Path('/run/samurai-wifi/mcfg-state/source-manifest-private.json').read_text())
assert len(manifest)==173 and manifest==json.loads((root/'k207-stock-mcfg-inventory/mcfg-source-manifest-private.json').read_text())
fwroot=Path('/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai')
assert all(sha(fwroot/name)==item['sha256'] for name,item in manifest.items())
assert all(not p.name.startswith('samurai-validation') for p in Path('/run/samurai-wifi/tftp-rw').iterdir())
remoteprocs = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert all(state == 'running' for state in remoteprocs.values())
log = subprocess.check_output(['dmesg']); (out / 'dmesg-private.txt').write_bytes(log)
faults = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
assert all(v == 0 for v in faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
result = dict(stage=207, same_second207_boot_verified=True,initial_final_health_observation_failed=True, rebooted_during_health_check=False, partitions_flashed=[], new_tftp_running=True, cache_private_tmpfs_32m=True, default_bt185_and_original_helper_config_restored=True, nv_sources_unchanged=True, remoteprocs=remoteprocs, taint=0, fault_counts=faults, gnss_session_terminal_and_test_files_removed=True, gnss_enabled=0, idle_location_before=late, late_idle_location_normalized=normalized, signals_location=False, gps_refresh_rate=30, assistance_current_independently_verified=True, assistance_hours=validity['hours'], gnss_real_fix_obtained=bool(test['valid_gga'] or test['raw_fix_reports'] or test['locations']), positive_cnr_fields=test['positive_cnr_fields'], modem_power_state=int(modem['PowerState']), modem_state=int(modem['State']), failed_reason=int(modem['StateFailedReason']), tftp_bootstrap_mcfg_requests_retested=True,stock_mcfg_auto_staging_verified=True,existing_ntp_sources_manually_refreshed=True, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
