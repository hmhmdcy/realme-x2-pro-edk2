from pathlib import Path
import hashlib,json,os,subprocess,tarfile
os.umask(0o077)
out=Path('/var/lib/samurai/k190-mm-build');sdk=Path('/var/lib/samurai/k190-mm-sdk')
assert (out/'sdk-validation-private.json').is_file()
db=Path('/lib/apk/db/installed').read_bytes()
archive=out/'source.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='018b1d62ca4e2a05a903b706bd63e34663622594caf5384490c4900503aefc8c'
destination=out/'source'
if not destination.exists():
 destination.mkdir()
 with tarfile.open(archive) as tar:tar.extractall(destination,filter='data')
source=next(destination.iterdir())
distro_patch=(out/'0001-intel-XMM7360-fix-big-endian-handling-of-ASN-integer.patch').read_bytes()
assert hashlib.sha512(distro_patch).hexdigest()=='f06e9b89acab5b61c5965658d62551b0f168066384674f7c4dd56feb6f811c82c640470e634e32d8c4ef62290588cf974aa5f213e5c67e797a06d33e61fa24ec'
lines=distro_patch.decode().splitlines(True);start=next(i for i,line in enumerate(lines) if line.startswith('@@'))+1
assert sum(line.startswith('@@') for line in lines)==1
hunk=[]
for line in lines[start:]:
 if line.startswith('-- '):break
 assert line[0] in ' +-'
 hunk.append(line)
before=''.join(line[1:] for line in hunk if line[0] in ' -');after=''.join(line[1:] for line in hunk if line[0] in ' +')
intel=source/'src/plugins/intel/mm-xmmrpc-xmm7360-protocol.c';original=intel.read_text();assert original.count(before)==1
intel.write_text(original.replace(before,after))
patched=(out/'mm-shared-qmi-patched.c').read_bytes()
assert hashlib.sha256(patched).hexdigest()=='a9e6c2765e07683bf84e1876d5ecb1cba64e71db25cbe561816c56ff4efabdfa'
(source/'src/mm-shared-qmi.c').write_bytes(patched)
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
 '-Dtests=false','-Dexamples=false'], 'configure')
run([str(sdk/'usr/bin/ninja'),'-C',str(out/'build'),'-j2','src/ModemManager'],'compile')
assert Path('/lib/apk/db/installed').read_bytes()==db
candidate=out/'build/src/ModemManager';assert candidate.is_file()
run([str(sdk/'usr/bin/readelf'),'-h','-d',str(candidate)],'candidate-elf')
report=dict(stage=190,candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(patched).hexdigest(),package_database_unchanged=True,compiled=True)
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
