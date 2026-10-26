from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222')
assert not private.exists();private.mkdir(mode=0o700)
for name in ['host.py','refresh-usb-endpoint.ps1']:
 (here/name).write_text((here.parent/'kernel221'/name).read_text().replace('kernel221','kernel222').replace('strict_usb221','strict_usb222').replace('Authenticated221','Authenticated222').replace('K221','K222'))
code=(here.parent/'kernel220/collect-baseline.py').read_text().replace('k220-','k222-').replace('stage=220','stage=222').replace('k219-runtime/boot-id-private.txt','k221-baseline/boot-id-private.txt').replace('k219-r6-package-candidates/forward-manifest.json','k220-r7-package-candidates/forward-manifest.json').replace('installed_r6_payload_records_verified','installed_r7_payload_records_verified').replace('Current219 boot/module/r6 payloads','Current219 boot/module/r7 payloads')
(here/'collect-baseline.py').write_text(code)
state=dict(stage=222,full_peripheral_goal_active=True,transition_pending=False,previous='221 readonly constellation/blacklist evidence verified; boot219/e49/r7/r2 retained',next='Inspect standard exposure controls and actual capture-sequence association before implementing truthful manual modes')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print('K222_PREPARED')
