"""Prepare a coherent k296 build and actual-k295 guarded deployment paths."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel295'
def save(name,s):
 p=ROOT/name;assert not p.exists(),name
 if p.suffix=='.py':compile(s,str(p),'exec')
 p.write_text(s)
def stage(s):
 return s.replace('kernel295','kernel296').replace('k295','k296').replace('K295','K296').replace('initramfs295','initramfs296').replace('modules295','modules296').replace('stage=295','stage=296').replace('kernel_build=295','kernel_build=296').replace("'#295 '","'#296 '").replace('"#295 "','"#296 "').replace("['kernel_build']==295","['kernel_build']==296")
commit=json.loads((ROOT/'source-validation.json').read_text())['commit']
s=stage((OLD/'build-boot-kernel.py').read_text()).replace('d249946aefa1a01d99fd5484825a4458423b7348',commit).replace('891bd0f83a9bb94b0e699ba7f22e13febdf88d0ac246f039936c9b91159addb8','f084bcf761c222cb77ea00ecd26b944f40401de8abc9a71b308c4d0a9963871a')
s=s.replace("ROOT.parent/'kernel294/boot-candidate-build-validation.json'","ROOT.parent/'kernel295/boot-candidate-build-validation.json'").replace('completed-boot294-r2','completed-boot295').replace("KBUILD_BUILD_VERSION='295'","KBUILD_BUILD_VERSION='296'")
save('build-boot-kernel.py',s)
s=(OLD/'host.py').read_text().replace('camera294_transport','camera295_transport').replace("'kernel294/host.py'","'kernel295/host.py'").replace("/kernel295'","/kernel296'")
(ROOT/'host.py').write_text(s)
for name in ['package-boot-candidate.py','stage-device-modules.py','native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-new-runtime.py','flash-logdump.py','prepare-transition.py','check-transition-readiness.py']:
 s=stage((OLD/name).read_text())
 s=s.replace('k294-work','k295-work').replace("'#294 '","'#295 '").replace('samurai-k294+','samurai-k295+').replace('current294','current295').replace('current_boot294','current_boot295')
 if name=='check-transition-readiness.py':s=s.replace('82a370391b01c5667add46607215af171a918a6023a34ad805ffc7a9f649d331','ddd66658c711ff45efc0e578e291affc98a1301f8700d7bb88e47af7bc95b0b6').replace('current_kernel_build=294','current_kernel_build=295')
 save(name,s)
for name in ['samurai-stats.c','samurai-optical.c','native-stats.py','launch-stats.py','poll-stats.py','native-optical.py','launch-optical.py','poll-optical.py','analyze-optical.py','analyze-stats-color.py','analyze-frame-association.py','native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py','inspect-layering.py','inspect-ssc-failure.py','restore-desktop.py']:
 save(name,stage((OLD/name).read_text()))
print('Prepared independent build, standard-API probes and actual-k295 transition guards.')
