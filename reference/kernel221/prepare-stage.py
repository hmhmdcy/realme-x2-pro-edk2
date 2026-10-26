from pathlib import Path
import json
here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel221')
assert not private.exists();private.mkdir(mode=0o700)
(here/'host.py').write_text((here.parent/'kernel220/host.py').read_text().replace('kernel220','kernel221').replace('strict_usb220','strict_usb221').replace('Authenticated220','Authenticated221'))
(here/'refresh-usb-endpoint.ps1').write_text((here.parent/'kernel220/refresh-usb-endpoint.ps1').read_text().replace('kernel220','kernel221').replace('K220','K221'))
state=dict(stage=221,full_peripheral_goal_active=True,transition_pending=False,previous='220 r7 exposure metadata repair deployed and verified',next='Freshly authenticate current boot, inspect read-only GNSS and modem initialization state; retain camera stack')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
print('K221_PREPARED_NO_DEVICE_OPERATION')
