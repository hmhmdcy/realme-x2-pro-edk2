from pathlib import Path
import shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
stage=SDK/'private/camss316-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'gst-hardware-probe.c',stage/'gst-hardware-probe.c')
q=subprocess.run(['chroot',str(SDK),'pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-allocators-1.0'],capture_output=True,text=True,check=True)
q=subprocess.run(['chroot',str(SDK),'gcc','-O2','-Wall','-Wextra','-Werror','/private/camss316-runtime/gst-hardware-probe.c',*q.stdout.split(),'-o','/private/camss316-runtime/gst-hardware-probe'],capture_output=True)
(host.PRIVATE/'gst-probe-build.log').write_bytes(q.stdout+q.stderr)
print(q.stderr.decode())
if q.returncode:raise SystemExit(q.returncode)
shutil.copyfile(HERE/'pw-hardware-probe.c',stage/'pw-hardware-probe.c')
q=subprocess.run(['chroot',str(SDK),'gcc','-std=gnu11','-O2','-Wall','-Wextra','-Wno-misleading-indentation',
 '-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2',
 '/private/camss316-runtime/pw-hardware-probe.c','/work/pipewire263-broadcast/build/src/pipewire/libpipewire-0.3.so.0.1609.0',
 '-o','/private/camss316-runtime/pw-hardware-probe'],capture_output=True)
(host.PRIVATE/'pw-probe-build.log').write_bytes(q.stdout+q.stderr)
print(q.stderr.decode());raise SystemExit(q.returncode)
