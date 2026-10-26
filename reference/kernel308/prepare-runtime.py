"""Compile the reviewed AWB application and package matching candidate files."""
from pathlib import Path
import io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE=SDK/'work/libcamera299-inline'
stage=SDK/'private/camss308-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'awb-smoke.cpp',stage/'awb-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/work/libcamera299-inline/include','-I/work/libcamera299-inline/output/include',
 '/private/camss308-runtime/awb-smoke.cpp','-L/work/libcamera299-inline/output/src/libcamera',
 '-L/work/libcamera299-inline/output/src/libcamera/base',
 '-Wl,-rpath-link,/work/libcamera299-inline/output/src/libcamera/base',
 '-lcamera','-lcamera-base','-pthread','-o','/private/camss308-runtime/awb-smoke'],capture_output=True,timeout=180)
(host.PRIVATE/'application-compile.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print(q.stderr.decode());raise SystemExit(q.returncode)
files={
 'bin/awb-smoke':stage/'awb-smoke',
 'bin/pipeline-fixture':host.PRIVATE.parent/'kernel305/pipeline-fixture305-aarch64-private',
 'lib/libcamera.so.0.7':TREE/'output/src/libcamera/libcamera.so.0.7.2',
 'lib/libcamera-base.so.0.7':TREE/'output/src/libcamera/base/libcamera-base.so.0.7.2',
 'ipa/ipa_camss_vfe.so':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa/ipa_camss_vfe.so.sign':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
 'proxy/camss_ipa_proxy':TREE/'output/src/libcamera/proxy/worker/camss_ipa_proxy',
 'profile/imx319.yaml':HERE/'imx319-awb.yaml',
 'profile/s5k3m5.yaml':HERE/'s5k3m5-awb.yaml',
}
archive=host.PRIVATE/'awb-runtime.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw)
        item.mode=0o700 if name.startswith(('bin/','proxy/')) else 0o600
        tar.addfile(item,io.BytesIO(raw))
print('Compiled AWB application and packaged matching IPA/proxy/library bundle.')
