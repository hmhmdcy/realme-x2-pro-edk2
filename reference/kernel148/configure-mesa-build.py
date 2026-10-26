"""Configure an isolated native Turnip build; never install over system Mesa."""
from pathlib import Path
import os,subprocess,hashlib,tarfile,json
sdk=Path('/tmp/k148-sdk'); base=Path('/var/lib/samurai/k148-mesa');base.mkdir(mode=0o700,exist_ok=True)
source=base/'mesa-26.2.4'; archive=Path('/var/lib/samurai/k148-sdk-apks/mesa-26.2.4.tar.xz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9'
if not source.exists():
    with tarfile.open(archive) as t: t.extractall(base,filter='data')
gccdir=next((sdk/'usr/lib/gcc').glob('aarch64-*/*'))
common=' --sysroot='+str(sdk)+' -B'+str(gccdir)+'/ -B'+str(sdk/'usr/bin')+'/'
env=dict(os.environ,PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],
    LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'),
    PYTHONPATH=str(sdk/'usr/lib/python3.14/site-packages'),
    PKG_CONFIG_SYSROOT_DIR=str(sdk),PKG_CONFIG_LIBDIR=str(sdk/'usr/lib/pkgconfig')+':'+str(sdk/'usr/share/pkgconfig'),
    CC=str(sdk/'usr/bin/gcc')+common,CXX=str(sdk/'usr/bin/g++')+common,
    LDFLAGS='-Wl,-rpath-link,'+str(sdk/'usr/lib'),BISON_PKGDATADIR=str(sdk/'usr/share/bison'),
    M4=str(sdk/'usr/bin/m4'))
(base/'build-env-private.json').write_text(json.dumps(env,indent=2)+'\n')
cmd=[str(sdk/'usr/bin/meson'),'setup',str(base/'build'),str(source),'--buildtype=release','--prefix='+str(base/'install'),
    '-Dplatforms=wayland','-Dgallium-drivers=[]','-Dvulkan-drivers=freedreno','-Dfreedreno-kmds=msm',
    '-Dllvm=disabled','-Dglx=disabled','-Degl=disabled','-Dopengl=false','-Dgles1=disabled','-Dgles2=disabled',
    '-Dgbm=disabled','-Dgallium-va=disabled','-Dvideo-codecs=[]','-Dperfetto=false',
    '-Dtools=[]','-Dbuild-tests=false','-Dvalgrind=disabled','-Dlibunwind=disabled','--wrap-mode=nofallback']
if (base/'build/meson-private/coredata.dat').exists():cmd.insert(2,'--reconfigure')
with (base/'configure-private.log').open('wb') as f: result=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
print('MESA_CONFIGURE_EXIT='+str(result.returncode));raise SystemExit(result.returncode)
