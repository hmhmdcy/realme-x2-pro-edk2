from pathlib import Path
import re

here=Path(__file__).resolve().parent
names=[('inspect-r11-full-features.py','inspect-full-features.py'),
       ('collect-r11-forward-packages.py','collect-forward-packages.py'),
       ('host-r11-runtime-qa.py','host-runtime-qa.py'),
       ('stage-r11-packages.py','stage-r12-packages.py')]
replacements={
 'kernel224':'kernel225','stage=224':'stage=225',
 'libcamera224-r11':'libcamera225','samurai-camera-config224-r11':'samurai-camera-config225',
 'packages224-r11':'packages225','packages-config224-r11':'packages-config225',
 'candidate224-r11':'candidate225','samurai-camera224-r11':'samurai-camera225-r12',
 'k224-r11':'k225-r12','k224-baseline':'k225-baseline',
 'camera-forward-repo-r11':'camera-forward-repo','camera-selected-repo-r11':'camera-selected-repo',
 'r11-package-build-validation.json':'package-build-validation.json',
 'r11-full-feature-configuration-validation.json':'full-feature-configuration-validation.json',
 'r11-forward-package-artifact-validation.json':'forward-package-artifact-validation.json',
 'r11-host-runtime-qa-validation.json':'host-runtime-qa-validation.json',
 'r11-staging-validation.json':'staging-validation.json',
 'r11-bundle':'r12-bundle','r11-candidate-bundle':'r12-candidate-bundle',
 'r11-transfer-offset':'r12-transfer-offset',
 '99990.7.2-r11':'99990.7.2-r12','0.1.0-r6':'0.1.0-r7',
 'k223-r8-package-candidates':'k224-r11-package-candidates',
 '99990.7.2-r8':'99990.7.2-r11','0.1.0-r3':'0.1.0-r6',
 'upstream_verifier_uses_current_r11_core_and_base':'upstream_verifier_uses_current_r12_core_and_base',
 'actual_seven_r8_rollback_apks_signatures_hashes_and_current_payloads_verified':'actual_seven_r11_rollback_apks_signatures_hashes_and_current_payloads_verified',
 }
pattern=re.compile('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)))
for source,target in names:
 text=(here.parent/'kernel224'/source).read_text();text=pattern.sub(lambda m:replacements[m.group()],text)
 if target=='stage-r12-packages.py':
  assert "rollback=root/'k224-r11-package-candidates'" in text and "'99990.7.2-r11'" in text and "'0.1.0-r6'" in text
  text=text.replace('retain actual r8 rollback','retain actual r11 rollback')
 compile(text,target,'exec');(here/target).write_text(text)
print('Separate r12 candidate QA and actual r11/r6 rollback staging prepared.')
