"""Compile the public request probe against this candidate's matching ABI."""
from pathlib import Path
import shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss315-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'raw-smoke.cpp',stage/'raw-smoke.cpp')
command=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/work/libcamera299-inline/include','-I/work/libcamera299-inline/output/include',
 '/private/camss315-runtime/raw-smoke.cpp','-L/work/libcamera299-inline/output/src/libcamera',
 '-L/work/libcamera299-inline/output/src/libcamera/base','-Wl,-rpath-link,/work/libcamera299-inline/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-pthread','-o','/private/camss315-runtime/raw-smoke']
q=subprocess.run(command,capture_output=True,timeout=150)
(host.PRIVATE/'runtime-build.log').write_bytes(q.stdout+q.stderr)
print(q.stderr.decode());raise SystemExit(q.returncode)
