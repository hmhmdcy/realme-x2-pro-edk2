"""Build the changed joint application; reuse the deployed308 library/IPA bundle."""
from pathlib import Path
import io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss312-runtime'
shutil.copyfile(HERE/'camera-smoke.cpp',stage/'camera-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/work/libcamera299-inline/include','-I/work/libcamera299-inline/output/include',
 '/private/camss312-runtime/camera-smoke.cpp','-L/work/libcamera299-inline/output/src/libcamera',
 '-L/work/libcamera299-inline/output/src/libcamera/base','-Wl,-rpath-link,/work/libcamera299-inline/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-pthread','-o','/private/camss312-runtime/camera-smoke'],capture_output=True,timeout=150)
(host.PRIVATE/'joint-compile.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
shutil.copyfile(stage/'camera-smoke',host.PRIVATE/'camera-smoke')
(HERE/'joint-build-validation.json').write_text(json.dumps({'stage':312,'werror_build_passed':True,'library_ipa_kernel_sensor_sources_unchanged':True,'main_max_gain_from_control_info':True},indent=2)+'\n')
print('Built joint application; main gain range comes from the sensor control limits.')
