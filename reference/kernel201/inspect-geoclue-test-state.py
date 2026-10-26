from pathlib import Path
import dbus,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-geoclue-test';r=dict(files={p.name:p.stat().st_size for p in out.iterdir()},drop_exists=Path('/etc/geoclue/conf.d/99-samurai-gnss-test.conf').exists(),desktop_exists=Path('/usr/share/applications/org.realme.SamuraiGNSSValidation.desktop').exists())
p=out/'client-result-private.json'
if p.exists() and p.stat().st_size:r['client']=json.loads(p.read_text())
p=out/'client-errors-private.txt'
if p.exists():r['client_errors']=p.read_text()
bus=dbus.SystemBus(private=True);r['geoclue_owned']=bus.name_has_owner('org.freedesktop.GeoClue2')
if r['geoclue_owned']:
 obj=bus.get_object('org.freedesktop.GeoClue2','/org/freedesktop/GeoClue2/Manager');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');r['geoclue_manager']=dict(props.GetAll('org.freedesktop.GeoClue2.Manager'))
mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');r['mm_enabled']=int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));bus.close();print(json.dumps(r,default=str))
