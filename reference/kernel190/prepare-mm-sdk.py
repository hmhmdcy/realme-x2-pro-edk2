"""Native signed-package SDK, extracted without changing the installed package set."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess

os.umask(0o077)
out=Path('/var/lib/samurai/k190-mm-build');out.mkdir(mode=0o700)
sdk=Path('/var/lib/samurai/k190-mm-sdk');sdk.mkdir(mode=0o755)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
db=Path('/lib/apk/db/installed').read_bytes()
def run(args,name,timeout=300,env=None):
    print(name,flush=True)
    with (out/(name+'-private.log')).open('wb') as log:
        subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout,env=env)

extra=out/'extra-apks';extra.mkdir()
run(['apk','--no-cache','fetch','--recursive','--output',str(extra),'dbus-dev','libgudev-dev','eudev-dev','elogind-dev','polkit-dev'], 'fetch-extra')
packages=[]
for directory in ['/var/lib/samurai/k148-sdk-apks','/var/lib/samurai/k184-libssc-deps-apks',str(extra)]:
    packages.extend(sorted(Path(directory).glob('*.apk')))
assert len(packages)>=117
for i,p in enumerate(packages):
    run(['apk','verify',str(p)],'verify-'+str(i),30)
    run(['apk','extract','--force-overwrite','--destination',str(sdk),str(p)],'extract-'+str(i),60)

runtime=['libglib-2.0.so.0','libgobject-2.0.so.0','libgio-2.0.so.0','libgmodule-2.0.so.0',
 'libqmi-glib.so.5','libmbim-glib.so.4','libqrtr-glib.so.0','libpcre2-8.so.0','libffi.so.8','libz.so.1','libintl.so.8',
 'libgudev-1.0.so.0','libudev.so.1','libelogind.so.0','libpolkit-gobject-1.so.0','libdbus-1.so.3']
hashes={}
closure=subprocess.run(['ldd']+['/usr/lib/'+n for n in runtime],capture_output=True,check=True).stdout.decode()
(out/'runtime-closure-private.txt').write_text(closure)
originals={Path('/usr/lib')/n for n in runtime}|{Path(n) for n in re.findall(r'=> (/[^ ]+) \(',closure)}
for original in originals:
    if 'ld-musl' in original.name:continue
    assert original.is_file(),original.name
    raw=original.read_bytes();hashes[original.name]=hashlib.sha256(raw).hexdigest()
    for dest in {sdk/'usr/lib'/original.name,sdk/'usr/lib'/original.resolve().name}:
        if dest.is_symlink():dest.unlink()
        dest.write_bytes(raw)
link=sdk/'usr/lib/libintl.so'
if not link.exists():link.symlink_to('libintl.so.8')
assert Path('/lib/apk/db/installed').read_bytes()==db
report=dict(signed_packages=len(packages),package_database_unchanged=True,runtime_hashes=hashes)
(out/'sdk-validation-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(signed_packages=len(packages),package_database_unchanged=True)))
