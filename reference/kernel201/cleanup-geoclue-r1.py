from pathlib import Path
import configparser,dbus,hashlib,json,os,signal,stat,time
root=Path('/var/lib/samurai');out=root/'k201-geoclue-test';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');assert not props.Get('org.freedesktop.GeoClue2.Manager','InUse')
mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');pid=int(daemon.GetConnectionUnixProcessID(daemon.GetNameOwner('org.freedesktop.GeoClue2')))
assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()=='e8d6416e6043f877b6ba008d535ad72ed5fe6ab131921db3ec62842962dfe2b6'
os.kill(pid,signal.SIGTERM)
for unused in range(30):
 if not bus.name_has_owner('org.freedesktop.GeoClue2'):break
 time.sleep(.1)
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
drop=Path('/etc/geoclue/conf.d/99-samurai-gnss-test.conf');mode=stat.S_IMODE(drop.parent.stat().st_mode)
config=configparser.ConfigParser(interpolation=None);config.read(drop);assert config['org.realme.SamuraiGNSSValidation']['users']=='10000;'
assert Path('/etc/geoclue/geoclue.conf').read_bytes()==(root/'k201-geoclue-install/geoclue.conf-private').read_bytes()
(out/'test-dropin-private.conf').write_bytes(drop.read_bytes());drop.unlink()
desktop=Path('/usr/share/applications/org.realme.SamuraiGNSSValidation.desktop');assert 'samurai-gnss-validation' in desktop.read_text();desktop.unlink()
os.chmod(drop.parent,0o755)
r=dict(stage=201,first_client_access_denied=True,geoclue_inactive_before_cleanup=True,temporary_app_and_dropin_removed=True,base_configuration_unchanged=True,config_directory_mode_before=oct(mode),config_directory_mode_after='0o755',first_parent_cleanup_identity_assertion_failure_recorded=True)
(out/'separate-cleanup.json').write_text(json.dumps(r,indent=2)+'\n');bus.close();print(json.dumps(r))
