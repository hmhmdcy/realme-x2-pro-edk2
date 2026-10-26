from pathlib import Path
import dbus,json,subprocess,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-assist-watch';assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0;bus.close()
state=Path('/var/lib/samurai/gnss-assist/watch-state.json');before=json.loads(state.read_text());assert before['running'] and not before['active'] and before['worker_starts']==0
(out/'before-stop.json').write_text(json.dumps(before,indent=2)+'\n')
for action in ['stop','start']:
 p=subprocess.run(['rc-service','samurai-gnss-assist',action],capture_output=True,text=True,timeout=20);(out/(action+'-private.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0
 if action=='stop':assert not json.loads(state.read_text())['running']
time.sleep(3);after=json.loads(state.read_text());assert after['running'] and not after['active'] and after['worker_starts']==0
r=dict(stage=201,idle_service_does_not_start_workers=True,idle_stop_and_restart_passed=True,worker_starts_before_application=0,openrc_default_enabled=Path('/etc/runlevels/default/samurai-gnss-assist').exists())
(out/'idle-summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
