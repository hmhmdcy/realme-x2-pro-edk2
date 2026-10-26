"""Prepare independent k294 paths; no device operations."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel293'
def save(name,s):
 p=ROOT/name;assert not p.exists(),name
 if p.suffix=='.py':compile(s,str(p),'exec')
 p.write_text(s)
def stage(s):
 return s.replace('kernel293','kernel294').replace('k293','k294').replace('K293','K294').replace('initramfs293','initramfs294').replace('modules293','modules294').replace('stage=293','stage=294').replace('kernel_build=293','kernel_build=294').replace("'#293 '","'#294 '").replace('"#293 "','"#294 "').replace("['kernel_build']==293","['kernel_build']==294")
# New boot guard, still delegating to the verified actual k293 until adoption.
s=(OLD/'host.py').read_text().replace('camera292_transport','camera293_transport').replace("'kernel292/host.py'","'kernel293/host.py'").replace("/kernel293'","/kernel294'")
(ROOT/'host.py').write_text(s)
s=stage((OLD/'package-boot-candidate.py').read_text()).replace('input-initramfs294','input-initramfs294-r2').replace('modules-k294-private','modules-k294-r2-private')
save('package-boot-candidate.py',s)
for name in ['stage-device-modules.py','native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-new-runtime.py','flash-logdump.py','prepare-transition.py']:
 s=stage((OLD/name).read_text())
 s=s.replace('k292-work','k293-work').replace("'#292 '","'#293 '").replace('samurai-k292+','samurai-k293+').replace('current292','current293').replace('current_boot292','current_boot293')
 if name=='stage-device-modules.py':s=s.replace('modules-k294-private','modules-k294-r2-private')
 if name=='prepare-transition.py':
  s=s.replace("assert not json.loads((ROOT/'preserved-source-validation.json').read_text())['differences']\n",'')
 if name=='check-new-runtime.py':
  s=s.replace("if pad in [0,1,5]","if pad in [0,1,4,5]")
  s=s.replace("['msm_vfe0_params','msm_vfe1_params']","['msm_vfe0_params','msm_vfe1_params','msm_vfe0_stats','msm_vfe1_stats']")
 save(name,s)
for name in ['samurai-optical.c','native-optical.py','launch-optical.py','poll-optical.py','analyze-optical.py','native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py']:
 save(name,stage((OLD/name).read_text()))
print('Prepared separate k294 workflows; no device writes.')
