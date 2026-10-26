from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel220')
assert not private.exists();private.mkdir(mode=0o700)
(here/'refresh-usb-endpoint.ps1').write_text((here.parent/'kernel219/refresh-usb-endpoint.ps1').read_text().replace('kernel219','kernel220').replace('K219','K220'))
r=dict(stage=220,previous_goal_turn='progress: boot219 timing fixes and full r6/r1 deployment physically verified,512 native archive members and7750 public mirror files checked',
 full_peripheral_goal_active=True,transition_pending=False,next='Authenticate current device and inspect standard exposure-control/configuration timing; preserve all219 deployment and rollback inputs')
(private/'current-work-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
