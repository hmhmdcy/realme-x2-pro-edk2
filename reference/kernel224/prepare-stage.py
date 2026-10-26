from pathlib import Path
import json

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel224')
assert not private.exists();private.mkdir(mode=0o700)
for name in ['host.py','refresh-usb-endpoint.ps1']:
 text=(here.parent/'kernel223'/name).read_text().replace('kernel223','kernel224').replace('strict_usb223','strict_usb224').replace('Authenticated223','Authenticated224').replace('K223','K224')
 (here/name).write_text(text)
text=(here.parent/'kernel223/collect-baseline.py').read_text().replace('k223-baseline','k224-baseline').replace('k222-baseline/boot-id-private.txt','k223-baseline/boot-id-private.txt').replace('stage=223','stage=224')
text=text.replace('k220-r7-package-candidates','k223-r8-package-candidates').replace('installed_r7_payload_records_verified','installed_r8_payload_records_verified').replace('r7 payloads','r8 payloads')
(here/'collect-baseline.py').write_text(text)
state=dict(stage=224,full_peripheral_goal_active=True,previous_goal_turn_classification='progress:223 deployed real SOF buffer association and r8 capture-control snapshots with native regressions',
 state='Current223 phone freshly authenticated; prepare RAW-only CPU statistics and metadata path before standard manual API',transition_pending=False,
 next='Implement and physically verify RAW-only exposure/gain statistics using original RAW buffers, without RGB buffer allocation or changing pixel data',
 transport='reference/kernel224/host.py',previous_guard='/var/lib/samurai/k223-baseline/boot-id-private.txt',
 current_deployment=dict(boot=219,image=183,camss='fae1ed40',imx471='e49dab26',framework='99990.7.2-r8',configuration='0.1.0-r3'),
 manual_api_still_open=True,gnss_cameras_bluetooth_sensors_cellular_and_all_other_peripherals_still_goal=True)
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print('K224_PREPARED')
