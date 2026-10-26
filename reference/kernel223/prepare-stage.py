from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel223')
assert not private.exists();private.mkdir(mode=0o700)
for name in ['host.py','refresh-usb-endpoint.ps1']:
 (here/name).write_text((here.parent/'kernel222'/name).read_text().replace('kernel222','kernel223').replace('strict_usb222','strict_usb223').replace('Authenticated222','Authenticated223').replace('K222','K223'))
code=(here.parent/'kernel222/collect-baseline.py').read_text().replace('k222-','k223-').replace('stage=222','stage=223').replace('k221-baseline/boot-id-private.txt','k222-baseline/boot-id-private.txt')
(here/'collect-baseline.py').write_text(code)
state=dict(stage=223,full_peripheral_goal_active=True,transition_pending=False,previous_goal_turn_classification='progress:222 reproduced request/capture mismatch and verified105 SOF events on a temporary candidate',next='Pair actual captured buffers with SOF, snapshot controls at capture time, then implement standard manual exposure semantics; current82c/e49/r7-r2 retained')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print('K223_PREPARED')
