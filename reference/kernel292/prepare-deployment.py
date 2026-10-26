"""Prepare current290 to independent292 deployment with the actual290 rollback."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel290'
def save(name,s):
 p=ROOT/name;assert not p.exists();compile(s,name,'exec') if p.suffix=='.py' else None;p.write_text(s)
def new_stage(s):
 s=s.replace('k288-work','CURRENT_BOOT_GUARD')
 s=s.replace('k290','k292').replace('kernel290','kernel292').replace('K290','K292').replace('stage=290','stage=292').replace('kernel_build=290','kernel_build=292').replace("'#290 '","'#292 '")
 s=s.replace('CURRENT_BOOT_GUARD','k290-work').replace("'#288 '","'#290 '").replace('samurai-k279candidate+','samurai-k290+').replace("['kernel_build']==290","['kernel_build']==292")
 return s
s=new_stage((OLD/'package-boot-candidate.py').read_text())
s=s.replace('input-initramfs290','input-initramfs292')
s=s.replace('kernel288/logdump-pix288-candidate-private.img','kernel290/logdump-k290-candidate-private.img').replace('8ec8b1e4d28ed76906ac9c9d31d8d791cab9d190c28d7f27224f8fb47e4aa56c','0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a')
save('package-boot-candidate.py',s)
save('stage-device-modules.py',new_stage((OLD/'stage-device-modules.py').read_text()))
for name in ['native-quiesce.py','restart-bootloader.py','launch-quiesce.py','poll-quiesce.py','submit-restart.py','refresh-usb-endpoint.ps1','bootstrap-postboot.py','check-new-runtime.py']:
 s=new_stage((OLD/name).read_text())
 if name in ['native-quiesce.py','restart-bootloader.py']:s=s.replace('current183','current290')
 save(name,s)
s=new_stage((OLD/'flash-logdump.py').read_text()).replace("package['kernel_build']==290","package['kernel_build']==292")
save('flash-logdump.py',s)
s=new_stage((OLD/'prepare-transition.py').read_text())
s=s.replace('kernel288/logdump-pix288-candidate-private.img','kernel290/logdump-k290-candidate-private.img').replace('current_boot288_verified','current_boot290_verified')
save('prepare-transition.py',s)
save('audit-preserved-sources.py',new_stage((OLD/'audit-preserved-sources.py').read_text()))
s=(ROOT.parent/'kernel291/final-health.py').read_text().replace("ROOT/'four-camera-regression-validation.json'","ROOT.parent/'kernel291/four-camera-regression-validation.json'").replace("ROOT/'physical-pixel-validation.json'","ROOT.parent/'kernel291/physical-pixel-validation.json'").replace("ROOT/'tele-pixel-validation.json'","ROOT.parent/'kernel291/tele-pixel-validation.json'")
s=s.replace('stage=291','stage=292').replace('k291-services-verified-private','k292-services-pre-transition-private').replace('k291-tools/final-health-private','k292-tools/pre-transition-health-private')
s=s.replace('final-health-new-boot-private','pre-transition-health-private').replace("ROOT/'final-health-validation.json'","ROOT/'pre-transition-health-validation.json'")
save('pre-transition-health.py',s)
print('Prepared independent kernel292 deployment; no transition submitted.')
