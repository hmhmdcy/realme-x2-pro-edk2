"""musl ldd accepts one object per call; enumerate each required runtime separately."""
from pathlib import Path
import hashlib,json,re,subprocess
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk');db=Path('/lib/apk/db/installed').read_bytes()
objects=['/usr/bin/ModemManager']+['/usr/lib/'+n for n in ['libglib-2.0.so.0','libgobject-2.0.so.0','libgio-2.0.so.0','libgmodule-2.0.so.0','libqmi-glib.so.5','libmbim-glib.so.4','libqrtr-glib.so.0','libgudev-1.0.so.0','libudev.so.1','libelogind.so.0','libpolkit-gobject-1.so.0','libdbus-1.so.3']]
paths=set();closures={}
for obj in objects:
 p=subprocess.run(['ldd',obj],capture_output=True,check=True);text=(p.stdout+p.stderr).decode()
 assert 'not found' not in text and 'Error' not in text
 closures[obj]=text
 paths.update(Path(n) for n in re.findall(r'=> (/[^ ]+) \(',text))
hashes={}
for original in paths:
 if 'ld-musl' in original.name:continue
 raw=original.read_bytes();hashes[original.name]=hashlib.sha256(raw).hexdigest()
 for dest in {sdk/'usr/lib'/original.name,sdk/'usr/lib'/original.resolve().name}:
  if dest.is_symlink():dest.unlink()
  dest.write_bytes(raw)
assert Path('/lib/apk/db/installed').read_bytes()==db
(out/'runtime-closures-corrected-private.json').write_text(json.dumps(closures,indent=2))
(out/'runtime-closure-hashes-private.json').write_text(json.dumps(hashes,indent=2))
print(json.dumps(dict(runtime_objects_checked=len(objects),runtime_dependency_libraries_copied=len(hashes),package_database_unchanged=True)))
