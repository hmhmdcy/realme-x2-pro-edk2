from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077)
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
source=next((out/'source').iterdir());patched=(source/'src/mm-shared-qmi.c').read_bytes()
db=Path('/lib/apk/db/installed').read_bytes()
gccdir=next((sdk/'usr/lib/gcc').glob('aarch64-*/*'))
common=' --sysroot='+str(sdk)+' -B'+str(gccdir)+'/ -B'+str(sdk/'usr/bin')+'/'
env=dict(os.environ,PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],
 LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'),PYTHONPATH=str(sdk/'usr/lib/python3.14/site-packages'),
 PKG_CONFIG_SYSROOT_DIR=str(sdk),PKG_CONFIG_LIBDIR=str(sdk/'usr/lib/pkgconfig')+':'+str(sdk/'usr/share/pkgconfig'),
 CC=str(sdk/'usr/bin/gcc')+common,LDFLAGS='-L/usr/lib -Wl,-rpath-link,'+str(sdk/'usr/lib'))
(out/'build-environment-private.json').write_text(json.dumps(env,indent=2))
def run(args,name,timeout=1200):
 print(name,flush=True)
 with (out/(name+'-private.log')).open('wb') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=timeout,env=env)
run([str(sdk/'usr/bin/meson'),'setup',str(out/'build'),str(source),'--prefix=/usr','--sbindir=bin','--libdir=lib',
 '--libexecdir=/usr/libexec','--sysconfdir=/etc','--localstatedir=/var','--buildtype=release',
 '-Db_lto=true','-Dsystemdsystemunitdir=/usr/lib/systemd/system','-Ddbus_policy_dir=/usr/share/dbus-1/system.d',
 '-Dudevdir=/usr/lib/udev','-Dpolkit=permissive','-Dsystemd_journal=false','-Dsystemd_suspend_resume=true',
 '-Dvapi=false','-Dintrospection=false','-Dgtk_doc=false','-Dman=false','-Dbash_completion=false',
 '-Dtests=false','-Dexamples=false'], 'configure-resume')
run([str(sdk/'usr/bin/ninja'),'-C',str(out/'build'),'-j2','src/ModemManager'],'compile-resume')
assert Path('/lib/apk/db/installed').read_bytes()==db
candidate=out/'build/src/ModemManager';assert candidate.is_file()
run([str(sdk/'usr/bin/readelf'),'-h','-d',str(candidate)],'candidate-elf')
report=dict(stage=190,candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(patched).hexdigest(),package_database_unchanged=True,compiled=True)
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
