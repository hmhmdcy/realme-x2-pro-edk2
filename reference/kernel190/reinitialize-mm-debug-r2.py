from pathlib import Path
import json,subprocess
import host

ref=Path(__file__).resolve().parent
source=(ref/'reinitialize-mm-debug.py').read_text().replace('k190-mm-reinit','k190-mm-reinit-r2')
source=source.replace("owner=dbus_api.GetNameOwner(service);pid=int(dbus_api.GetConnectionUnixProcessID(owner))",'''def owner_now():
 try:return dbus_api.GetNameOwner(service)
 except dbus.DBusException as error:
  if error.get_dbus_name()=='org.freedesktop.DBus.Error.NameHasNoOwner':return None
  raise
owner=owner_now();assert owner is not None
pid=int(dbus_api.GetConnectionUnixProcessID(owner))''')
source=source.replace('while dbus_api.NameHasOwner(service) and dbus_api.GetNameOwner(service)==owner and time.monotonic()<deadline:',
 'while owner_now()==owner and time.monotonic()<deadline:')
source=source.replace('assert not dbus_api.NameHasOwner(service) or dbus_api.GetNameOwner(service)!=owner','assert owner_now()!=owner')
source=source.replace('if not dbus_api.NameHasOwner(service):','if owner_now() is None:')
source=source.replace('if dbus_api.NameHasOwner(service):\n   current_owner=dbus_api.GetNameOwner(service);',
 'current_owner=owner_now()\n  if current_owner is not None:\n   ')
source=source.replace('os.kill(pid,signal.SIGTERM)','dbus_api.ReloadConfig()\n os.kill(pid,signal.SIGTERM)')
source=source.replace("assert activation.read_bytes()==original","assert activation.read_bytes()==original\n dbus_api.ReloadConfig()")
path=ref/'mm-debug-r2-expanded.py';assert not path.exists();path.write_text(source)
compile(source,str(path),'exec')
try:p=host.ssh('python3 -',input=source.encode(),timeout=125)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'mm-debug-r2-failure-private.log').write_bytes(error.stdout+error.stderr);print(error.stderr.decode());raise
(host.PRIVATE/'mm-debug-r2-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(ref/'mm-debug-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
