from pathlib import Path
import json,re

here=Path(__file__).resolve().parent
assert json.loads((here/'r13-candidate-manual-matrix-validation.json').read_text())['frames']==1024
for flavour in ['candidate-threaded','candidate-isolated']:
 assert json.loads((here/f'lifecycle-r13-{flavour}-validation.json').read_text())['all40_requests_completed_or_cancelled']
replacements={
 'k224-r11-package-candidates':'k225-r13-package-candidates',
 'k224-r11-package-transaction':'k225-r13-package-transaction',
 'k224-baseline':'k225-baseline','k223-r8-package-candidates':'k224-r11-package-candidates',
 'stage=224':'stage=225','99990.7.2-r11':'99990.7.2-r13','99990.7.2-r8':'99990.7.2-r11',
 '0.1.0-r6':'0.1.0-r8','0.1.0-r3':'0.1.0-r6',
 'r11-native-preflight-validation.json':'r13-native-preflight-validation.json',
 'r11-package-install-validation.json':'r13-package-install-validation.json',
 'r11-preflight-host-private.log':'r13-preflight-host-private.log',
 'r11-install-host-private.log':'r13-install-host-private.log',
 'all_current_camera_payloads_match_r8_rollback':'all_current_camera_payloads_match_r11_rollback',
 'new_r11_camera_libraries_loaded':'new_r13_camera_libraries_loaded',
 'native_seven_package_r8_downgrade_simulation_passed':'native_seven_package_r11_downgrade_simulation_passed',
 'original_world_repositories_and_r8_payloads_retained':'original_world_repositories_and_r11_payloads_retained',
 }
pattern=re.compile('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)))
for source,target in [('native-r11-preflight.py','native-r13-preflight.py'),('install-r11-packages.py','install-r13-packages.py'),('reload-wireplumber.py','reload-wireplumber.py')]:
 text=(here.parent/'kernel224'/source).read_text();text=pattern.sub(lambda m:replacements[m.group()],text)
 if target=='native-r13-preflight.py':
  assert "k224-r11-package-candidates" in text and "99990.7.2-r11" in text and "0.1.0-r6" in text
  assert "samurai-camera-stack=0.1.0-r8" in text
 compile(text,target,'exec');(here/target).write_text(text)
print('R13 native seven-package preflight/install/reload prepared with actual R11/R6 rollback; no transaction sent.')
