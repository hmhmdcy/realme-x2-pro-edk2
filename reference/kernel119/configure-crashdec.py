from pathlib import Path
import runpy,subprocess,shutil,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
source=root/'mesa-26.2.4';build=root/'decode-build'
assert source.is_dir() and shutil.disk_usage(root).free>3*1024**3
out=Path('/mnt/e/edk2-samurai-out/kernel119/gpu-coredump');out.mkdir(exist_ok=True)
args=['meson','setup',str(build),str(source),'--wrap-mode=nofallback','-Dbuildtype=debugoptimized','-Dtools=freedreno','-Dgallium-drivers=[]','-Dvulkan-drivers=[]','-Dplatforms=[]','-Dglx=disabled','-Degl=disabled','-Dgbm=disabled','-Dopengl=false','-Dgles1=disabled','-Dgles2=disabled','-Dllvm=disabled','-Dvideo-codecs=[]','-Dbuild-tests=false']
if (build/'meson-private/coredata.dat').exists():args.extend(['--reconfigure','--clearcache'])
logfile=out/'meson-configure-private.txt'
if logfile.exists():
    for n in range(1,100):
        prior=out/f'meson-configure-private-attempt{n}.txt'
        if not prior.exists():logfile.rename(prior);break
with logfile.open('w') as log:
    p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=180)
print('CONFIGURE_EXIT',p.returncode)
print('\n'.join((out/'meson-configure-private.txt').read_text().splitlines()[-35:]))
raise SystemExit(p.returncode)
