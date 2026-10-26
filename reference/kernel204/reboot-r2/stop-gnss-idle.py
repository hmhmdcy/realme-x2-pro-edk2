from pathlib import Path
import dbus, json, os, subprocess, time

root = Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (root/'k204r2-before-reboot/boot-id-private.txt').read_bytes()
bus = dbus.SystemBus(private=True)
prop = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(prop.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
bus.close()
state_path = root/'gnss-assist/watch-state.json'
state = json.loads(state_path.read_text())
assert state['running'] and not state['active'] and state['worker_starts'] == state['worker_completions']
assert state['time_prepared'] and state['time_preparation_starts']==state['time_preparation_completions']>=1
pid = int(Path('/run/samurai-gnss-assist.pid').read_text())
args = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')
assert b'/usr/sbin/samurai-gnss-assist' in args and b'--watch' in args
subprocess.run(['rc-service', 'samurai-gnss-assist', 'stop'], check=True, timeout=20, capture_output=True)
time.sleep(1)
assert not Path('/proc/%d' % pid).exists()
assert not json.loads(state_path.read_text())['running']
assert (Path('/etc/runlevels/default')/'samurai-gnss-assist').resolve() == Path('/etc/init.d/samurai-gnss-assist')
(root/'k204r2-quiesce/gnss-idle-stop-verified.json').write_text(json.dumps(dict(gps_inactive=True, watcher_stopped=True, default_runlevel_preserved=True))+'\n')
print('K202_GNSS_IDLE_STOP_VERIFIED')
