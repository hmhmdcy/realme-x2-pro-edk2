"""Compile changed AF probe and fixture; package matching candidate artifacts."""
from pathlib import Path
import shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss313-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'af-smoke.cpp',stage/'af-smoke.cpp')
fixture=(HERE.parent/'kernel305/pipeline-fixture.c').read_text().replace('V4L2_CID_TEST_PATTERN,V4L2_CID_EXPOSURE',
 'V4L2_CID_FOCUS_ABSOLUTE,V4L2_CID_TEST_PATTERN,V4L2_CID_EXPOSURE')
(HERE/'pipeline-fixture.c').write_text(fixture)
commands=[['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/work/libcamera299-inline/include','-I/work/libcamera299-inline/output/include',
 '/private/camss313-runtime/af-smoke.cpp','-L/work/libcamera299-inline/output/src/libcamera',
 '-L/work/libcamera299-inline/output/src/libcamera/base','-Wl,-rpath-link,/work/libcamera299-inline/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-pthread','-o','/private/camss313-runtime/af-smoke'],
 ['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
 '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(HERE/'pipeline-fixture.c'),'-o',str(host.PRIVATE/'pipeline-fixture')]]
for n,command in enumerate(commands):
 q=subprocess.run(command,capture_output=True,timeout=150)
 (host.PRIVATE/('runtime-compile-'+str(n)+'.log')).write_bytes(q.stdout+q.stderr)
 if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
print('Built AF probe and fixture with focus control restoration.')
