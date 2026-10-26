from pathlib import Path
import hashlib,json,os,re,subprocess,tarfile
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
out=root/'k213-libcamera-build';sdk=root/'k213-libcamera-sdk';inputs=out/'inputs';db=Path('/lib/apk/db/installed').read_bytes()
assert not (out/'sdk-ready-private.json').exists()
packages=sorted((inputs/'apks').glob('*.apk'));assert len(packages)>=10
for i,path in enumerate(packages):
    for phase,args in [('verify',['apk','verify',str(path)]),('extract',['apk','extract','--force-overwrite','--destination',str(sdk),str(path)])]:
        with (out/(str(i)+'-'+phase+'-private.log')).open('wb') as log:subprocess.run(args,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=60)
names=['libyaml-0.so.2','libgnutls.so.30','libevent-2.1.so.7','libevent_pthreads-2.1.so.7','libevent_core-2.1.so.7','libevent_extra-2.1.so.7','libevent_openssl-2.1.so.7','libyuv.so.0','libEGL.so.1','libGLESv2.so.2','libunwind.so.8','libunwind-aarch64.so.8','libdrm.so.2','libgbm.so.1','libjpeg.so.8']
originals=[Path('/usr/lib')/name for name in names if (Path('/usr/lib')/name).is_file()]
closure=subprocess.run(['ldd',*map(str,originals)],capture_output=True,text=True,timeout=30);(out/'runtime-closure-private.txt').write_text(closure.stdout+closure.stderr)
paths=set(originals)|{Path(n) for n in re.findall(r'=> (/[^ ]+) \(',closure.stdout)}
hashes={}
for original in paths:
    if 'ld-musl' in original.name:continue
    assert original.is_file();data=original.read_bytes();hashes[str(original)]=hashlib.sha256(data).hexdigest()
    for target in {sdk/'usr/lib'/original.name,sdk/'usr/lib'/original.resolve().name}:
        if target.is_symlink():target.unlink()
        target.write_bytes(data)
for original in originals:
    name=original.name.split('.so',1)[0]+'.so';link=sdk/'usr/lib'/name
    if link.is_symlink():link.unlink()
    if not link.exists():link.symlink_to(original.resolve().name)
source_root=out/'source';source_root.mkdir(mode=0o700)
with tarfile.open(inputs/'source.tar.gz') as archive:archive.extractall(source_root,filter='data')
source=source_root/'libcamera-v0.7.2';assert source.is_dir()
gccdir=next((sdk/'usr/lib/gcc').glob('aarch64-*/*'));common=' --sysroot='+str(sdk)+' -B'+str(gccdir)+'/ -B'+str(sdk/'usr/bin')+'/'
env=dict(os.environ,PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'),PYTHONPATH=str(sdk/'usr/lib/python3.14/site-packages'),PKG_CONFIG_SYSROOT_DIR=str(sdk),PKG_CONFIG_LIBDIR=str(sdk/'usr/lib/pkgconfig')+':'+str(sdk/'usr/share/pkgconfig'),CC=str(sdk/'usr/bin/gcc')+common,CXX=str(sdk/'usr/bin/g++')+common,LDFLAGS='-L/usr/lib -Wl,-rpath-link,'+str(sdk/'usr/lib'))
(out/'build-environment-private.json').write_text(json.dumps(env,indent=2)+'\n')
for name,args in [('python-modules',['python3','-c','import jinja2,ply,yaml;print("modules ready")']),('compiler-version',[str(sdk/'usr/bin/g++'),'--version'])]:
    with (out/(name+'-private.log')).open('wb') as log:subprocess.run(args,env=env,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=20)
assert db==Path('/lib/apk/db/installed').read_bytes()
(out/'runtime-hashes-private.json').write_text(json.dumps(hashes,indent=2)+'\n')
report=dict(stage=213,independent_sdk_ready=True,signed_development_packages=len(packages),actual_installed_runtime_copied_into_sdk_only=True,package_database_unchanged=True,no_camera_product_replacement=True)
(out/'sdk-ready-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
