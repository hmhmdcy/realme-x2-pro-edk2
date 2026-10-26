"""Repackage current libraries with the unchanged, already compiled application."""
from pathlib import Path
import io,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE=SDK/'work/libcamera299-inline'
files={'bin/camera-smoke':SDK/'private/camss311-runtime/camera-smoke',
 'bin/pipeline-fixture':host.PRIVATE.parent/'kernel305/pipeline-fixture305-aarch64-private',
 'lib/libcamera.so.0.7':TREE/'output/src/libcamera/libcamera.so.0.7.2',
 'lib/libcamera-base.so.0.7':TREE/'output/src/libcamera/base/libcamera-base.so.0.7.2',
 'ipa/ipa_camss_vfe.so':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa/ipa_camss_vfe.so.sign':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
 'proxy/camss_ipa_proxy':TREE/'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
files.update({'profile/'+m+'.yaml':HERE/(m+'.yaml') for m in ['s5kgw1','imx471','imx319','s5k3m5']})
with tarfile.open(host.PRIVATE/'runtime.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith(('bin/','proxy/')) else 0o600
  tar.addfile(item,io.BytesIO(raw))
print('Packaged current candidate; no unchanged application rebuild.')
