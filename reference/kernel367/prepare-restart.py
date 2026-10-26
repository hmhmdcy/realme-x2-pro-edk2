"""Prepare a normal baseline restart with no partition write or A5 launch."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel366';P=host.PRIVATE
adopt=json.loads((P.parent/'kernel366/recovered-boot-adoption-private.json').read_text());guard=adopt['guard_path']
for name in ['native-quiesce.py','restart-bootloader.py','run-transition-step.py','check-transition.py']:
 s=(OLD/name).read_text().replace('k366','k367').replace('stage=366','stage=367')
 s=s.replace('/var/lib/samurai/k365-work/boot-id-private.txt',guard)
 if name=='check-transition.py':
  s=s.replace("old=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text())", "old=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text());old['firmware_boot_preserved_sha256']=json.loads((HERE.parent/'kernel366/build-package-validation.json').read_text())['boot_sha256']")
 (HERE/name).write_text(s);compile(s,name,'exec')
for name in ['camera-check.py','camera-check-body.py','inspect-services.py','final-state.py']:
 s=(OLD/name).read_text().replace('k366','k367').replace('stage=366','stage=367').replace("'stage':366","'stage':367")
 s=s.replace('/var/lib/samurai/k367-recovered/boot-id-private.txt','/var/lib/samurai/k367-work/boot-id-private.txt')
 s=s.replace('firmware_boot_stage=367','firmware_boot_stage=366')
 if name=='final-state.py':
  s=s.replace("b'/var/lib/samurai/k367-'","b'/var/lib/samurai/k366-',b'/var/lib/samurai/k367-'")
 (HERE/name).write_text(s);compile(s,name,'exec')
print('Prepared normal guarded restart, no image/firmware/partition update and no A5 CPU release.')
