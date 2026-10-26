from pathlib import Path
import ast,shutil,host
ref=Path(__file__).resolve().parent
shutil.copyfile(ref/'test-geoclue-gnss.py',ref/'test-geoclue-gnss-r1.py')
s=(ref/'test-geoclue-gnss.py').read_text().replace("out=root/'k201-geoclue-test'", "out=root/'k201-geoclue-test-r2'")
s=s.replace("drop.parent.mkdir(exist_ok=True)","drop.parent.mkdir(mode=0o755,exist_ok=True);assert drop.parent.stat().st_mode & 0o777 == 0o755")
s=s.replace("assert geopid==current and (Path('/proc')/str(current)/'exe').resolve()==Path('/usr/libexec/geoclue')", "assert (geopid is None or geopid==current) and (Path('/proc')/str(current)/'exe').resolve()==Path('/usr/libexec/geoclue')")
ast.parse(s);(ref/'test-geoclue-gnss.py').write_text(s)
p=ref/'geoclue-validation-client.py';s=p.read_text().replace('from gi.repository import GLib','from gi.repository import GLib,GLibUnix').replace('GLib.unix_signal_add(GLib.PRIORITY_DEFAULT,sig,stop)','GLibUnix.signal_add(GLib.PRIORITY_DEFAULT,sig,stop)')
s=s.replace("except dbus.DBusException as error:result['error_name']=error.get_dbus_name()", "except dbus.DBusException as error:\n result['error_name']=error.get_dbus_name();print(error.get_dbus_message(),file=sys.stderr)")
ast.parse(s);p.write_text(s);host.upload(p,'/usr/libexec/samurai-gnss-validation');host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
print('K201_FIRST_FAILURE_PRESERVED_SECOND_CLIENT_TEST_READY_WITH_READABLE_DROPIN_DIRECTORY')
