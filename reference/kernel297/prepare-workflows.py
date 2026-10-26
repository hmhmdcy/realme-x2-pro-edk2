"""Reuse completed workflows with explicit old/new boot identities and hashes."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kernel296'
def stage(s):
 for a,b in [('kernel296','kernel297'),('k296','k297'),('K296','K297'),('initramfs296','initramfs297'),('modules296','modules297'),
             ('stage=296','stage=297'),('kernel_build=296','kernel_build=297'),("'#296 '","'#297 '"),('"#296 "','"#297 "'),("['kernel_build']==296","['kernel_build']==297")]:
  s=s.replace(a,b)
 return s
def save(name,s):
 p=HERE/name;assert not p.exists(),name
 if p.suffix=='.py':compile(s,str(p),'exec')
 p.write_text(s)
commit=json.loads((HERE/'source-validation.json').read_text())['commit']
s=stage((OLD/'build-boot-kernel.py').read_text())
s=s.replace('f86906688666c0ebaabaeeec96c28d5741257f50',commit)
s=s.replace('f084bcf761c222cb77ea00ecd26b944f40401de8abc9a71b308c4d0a9963871a','82e39f7ea2ad2507417290cfbcd5754dd3f4ee431bb3a73b31e8f880e5e04233')
s=s.replace("ROOT.parent/'kernel295/boot-candidate-build-validation.json'","ROOT.parent/'kernel296/boot-candidate-build-validation.json'").replace('completed-boot295','completed-boot296')
s=s.replace("KBUILD_BUILD_VERSION='296'","KBUILD_BUILD_VERSION='297'")
save('build-boot-kernel.py',s)
for name in ['package-boot-candidate.py','stage-device-modules.py','native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py',
             'refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-new-runtime.py','flash-logdump.py','prepare-transition.py','check-transition-readiness.py']:
 s=stage((OLD/name).read_text())
 s=s.replace('k295-work','k296-work').replace("'#295 '","'#296 '").replace('samurai-k295+','samurai-k296+').replace('current295','current296').replace('current_boot295','current_boot296')
 if name=='check-transition-readiness.py':
  s=s.replace('ddd66658c711ff45efc0e578e291affc98a1301f8700d7bb88e47af7bc95b0b6','64616e8fd6e4327e6a07d5c738bea7b7707922703f8a69a97f11ec11af08605e').replace('current_kernel_build=295','current_kernel_build=296')
 save(name,s)
for name in ['samurai-stats.c','samurai-optical.c','native-stats.py','launch-stats.py','poll-stats.py','native-optical.py','launch-optical.py','poll-optical.py',
             'analyze-optical.py','analyze-stats-color.py','analyze-frame-association.py','native-four-camera-regression.py','launch-four-camera-regression.py',
             'poll-four-camera-regression.py','inspect-layering.py','inspect-ssc-failure.py','restore-desktop.py','analyze-statistics.py','analyze-optical-statistics.py']:
 save(name,stage((OLD/name).read_text()))
print('Prepared k297 workflows; current-k296 transition guards preserved, no execution.')
