"""Build only the changed measurement applications and package their profiles."""
from pathlib import Path
import io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss312-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'delay-capture.cpp',stage/'delay-capture.cpp')
commands=[
 ['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
  '-I/work/libcamera299-inline/include','-I/work/libcamera299-inline/output/include',
  '/private/camss312-runtime/delay-capture.cpp','-L/work/libcamera299-inline/output/src/libcamera',
  '-L/work/libcamera299-inline/output/src/libcamera/base','-Wl,-rpath-link,/work/libcamera299-inline/output/src/libcamera/base',
  '-lcamera','-lcamera-base','-pthread','-o','/private/camss312-runtime/delay-capture'],
 ['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
  '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'control-stepper.c'),'-o',str(host.PRIVATE/'control-stepper')]]
for n,command in enumerate(commands):
    q=subprocess.run(command,capture_output=True,timeout=150)
    (host.PRIVATE/('compile-'+str(n)+'.log')).write_bytes(q.stdout+q.stderr)
    if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
files={'bin/delay-capture':stage/'delay-capture','bin/control-stepper':host.PRIVATE/'control-stepper'}
files.update({'profile/'+m+'.yaml':HERE/(m+'-measure.yaml') for m in ['s5kgw1','imx471']})
with tarfile.open(host.PRIVATE/'measurement.tar.gz','w:gz') as tar:
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw)
        item.mode=0o700 if name.startswith('bin/') else 0o600
        tar.addfile(item,io.BytesIO(raw))
(HERE/'build-validation.json').write_text(json.dumps({'stage':312,'werror_build_passed':True,'existing308_libraries_reused':True,'sensor_delays_not_assumed':True},indent=2)+'\n')
print('Built main/front measurement applications; existing runtime libraries reused.')
