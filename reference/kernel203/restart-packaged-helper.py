from pathlib import Path
import dbus,hashlib,json,subprocess,time

root=Path('/var/lib/samurai');out=root/'k203-packaged-helper';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root/'k203-package-install/summary.json').read_text())['single_package_transaction_complete']
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==1 and not bus.name_has_owner('org.freedesktop.GeoClue2')
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');owner=str(daemon.GetNameOwner('org.freedesktop.ModemManager1'))
for label,command in [('global-policy',['apk','--no-network','policy','modemmanager','samurai-gnss-stack','samurai-gnss-assist']),('plain-mm-add-simulation',['apk','--no-network','add','--simulate','modemmanager'])]:
 p=subprocess.run(command,capture_output=True,text=True,timeout=30);(out/(label+'-private.log')).write_text(p.stdout+p.stderr);assert p.returncode==0
 if label=='global-policy':assert '1.25.95_git20261005-r1' in p.stdout and 'file:///var/lib/samurai/packages/gnss-203/packages.adb' in p.stdout
 else:assert not any(word in p.stdout for word in ['Installing','Upgrading','Downgrading','Purging','Reinstalling'])
watch=root/'gnss-assist/watch-state.json';before=json.loads(watch.read_text());assert before['running'] and not before['active'] and before['worker_starts']==before['worker_completions']==1 and before['time_preparation_starts']==before['time_preparation_completions']==3
for name in ['watch-state.json','last-result.json','time-preparation-result.json']:(out/('before-'+name)).write_bytes((root/'gnss-assist'/name).read_bytes())
old=int(Path('/run/samurai-gnss-assist.pid').read_text())
p=subprocess.run(['rc-service','samurai-gnss-assist','restart'],capture_output=True,text=True,timeout=35);(out/'restart-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
deadline=time.monotonic()+65
while time.monotonic()<deadline:
 state=json.loads(watch.read_text())
 if state['running'] and state['time_prepared'] and state['time_preparation_starts']==state['time_preparation_completions']==1:break
 time.sleep(1)
else:raise AssertionError('Inspect the same helper restart; do not repeat')
assert int(Path('/run/samurai-gnss-assist.pid').read_text())!=old and not Path('/proc/%d'%old).exists()
assert state['worker_starts']==state['worker_completions']==0 and not state['active']
assert state['source_sha256']==hashlib.sha256(Path('/usr/sbin/samurai-gnss-assist').read_bytes()).hexdigest()=='42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97'
assert str(daemon.GetNameOwner('org.freedesktop.ModemManager1'))==owner and int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==1;bus.close()
r=dict(stage=203,global_signed_repository_available=True,normal_mm_add_simulation_has_no_changes=True,packaged_helper_restarted_from_owned_source=True,old_idle_helper_exited=True,mm_process_not_restarted=True,source_sha256=state['source_sha256'],time_preparation=state['time_preparation_last_result'],time_preparation_count=1,data_workers=0,gps_enabled=0,mm_power_state=1)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
