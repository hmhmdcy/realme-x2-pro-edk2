from pathlib import Path
import json,shutil

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel225')
assert not private.exists();private.mkdir(mode=0o700)
for name in ['host.py','refresh-usb-endpoint.ps1']:
 text=(here.parent/'kernel224'/name).read_text().replace('kernel224','kernel225').replace('strict_usb224','strict_usb225').replace('Authenticated224','Authenticated225').replace('K224','K225')
 (here/name).write_text(text)
text=(here.parent/'kernel224/collect-baseline.py').read_text()
for a,b in [('k224-baseline','k225-baseline'),('k223-baseline/boot-id-private.txt','k224-baseline/boot-id-private.txt'),('stage=224','stage=225'),('k223-r8-package-candidates','k224-r11-package-candidates'),('installed_r8_payload_records_verified','installed_r11_payload_records_verified'),('r8 payloads','r11 payloads')]:text=text.replace(a,b)
(here/'collect-baseline.py').write_text(text)
archive=repo/'archive/NEXT-SESSION-through224-2026-10-16.md';assert not archive.exists();shutil.copyfile(repo/'NEXT-SESSION.md',archive)
state=dict(stage=225,full_peripheral_goal_active=True,
 previous_goal_turn_classification='progress:224 r11/r6 deployed with RAW automatic statistics, actual metadata, cancellation fixes and native regression',
 state='Preparing independent exposure/gain Auto/Manual controls and delayed source cookies; phone remains r11/r6',
 transition_pending=False,active_build_session=None,active_native_session=None,
 transport='reference/kernel225/host.py',previous_guard='/var/lib/samurai/k224-baseline/boot-id-private.txt',
 current_deployment=dict(boot=219,image=183,camss='fae1ed40',imx471='e49dab26',framework='99990.7.2-r11',configuration='0.1.0-r6'),
 next='Implement independent modes, ignore auto manual values, freeze transitions, start controls and captured effective-mode metadata; build and native-test before deployment',
 gnss_cameras_bluetooth_sensors_cellular_and_all_peripherals_still_goal=True)
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
(here/'README.md').write_text('# 225：标准曝光/增益控制进行中\n\n手机仍为已验证的r11/config-r6、boot219/e49/fae1。上一轮实际部署与回归通过。本轮实现独立Auto/Manual、Camera::start控制和捕获来源元数据，候选尚未部署；全外设goal保持active。\n')
print('Stage225 prepared; phone not modified.')
