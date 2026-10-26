"""Build the existing four-camera AWB probe, with optional joint AE."""
from pathlib import Path
import io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE=SDK/'work/libcamera299-inline'
stage=SDK/'private/camss311-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'camera-smoke.cpp',stage/'camera-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/work/libcamera299-inline/include','-I/work/libcamera299-inline/output/include',
 '/private/camss311-runtime/camera-smoke.cpp','-L/work/libcamera299-inline/output/src/libcamera',
 '-L/work/libcamera299-inline/output/src/libcamera/base','-Wl,-rpath-link,/work/libcamera299-inline/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-pthread','-o','/private/camss311-runtime/camera-smoke'],capture_output=True,timeout=180)
(host.PRIVATE/'application-compile.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
files={
 'bin/camera-smoke':stage/'camera-smoke',
 'bin/pipeline-fixture':host.PRIVATE.parent/'kernel305/pipeline-fixture305-aarch64-private',
 'lib/libcamera.so.0.7':TREE/'output/src/libcamera/libcamera.so.0.7.2',
 'lib/libcamera-base.so.0.7':TREE/'output/src/libcamera/base/libcamera-base.so.0.7.2',
 'ipa/ipa_camss_vfe.so':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa/ipa_camss_vfe.so.sign':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
 'proxy/camss_ipa_proxy':TREE/'output/src/libcamera/proxy/worker/camss_ipa_proxy',
}
files.update({'profile/'+model+'.yaml':HERE/(model+'.yaml') for model in ['s5kgw1','imx471','imx319','s5k3m5']})
with tarfile.open(host.PRIVATE/'runtime.tar.gz','w:gz') as tar:
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw)
        item.mode=0o700 if name.startswith(('bin/','proxy/')) else 0o600
        tar.addfile(item,io.BytesIO(raw))
print('Built runtime WB application and matching311 IPA/library/proxy bundle.')
