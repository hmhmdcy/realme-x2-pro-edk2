from pathlib import Path
import json
here=Path(__file__).resolve().parent
assert json.loads((here/'package-build-validation.json').read_text())['framework_and_config_packages_built']
for source,target in [('inspect-full-features.py','inspect-full-features.py'),('collect-forward-packages.py','collect-forward-packages.py'),('host-runtime-qa.py','host-runtime-qa.py'),('stage-r8-packages.py','stage-r9-packages.py')]:
 text=(here.parent/'kernel223'/source).read_text().replace('kernel223','kernel224').replace('k223-','k224-').replace('libcamera223','libcamera224').replace('packages223','packages224').replace('packages-config223','packages-config224').replace('samurai-camera-config223','samurai-camera-config224').replace('stage=223','stage=224').replace('candidate223','candidate224')
 text=text.replace('samurai-camera223-r8','samurai-camera224-r9').replace('r8','r9').replace('0.1.0-r3','0.1.0-r4')
 if source=='stage-r8-packages.py':
  text=text.replace('k220-r7-package-candidates','k223-r8-package-candidates').replace('99990.7.2-r7','99990.7.2-r8').replace('0.1.0-r2','0.1.0-r3').replace('r7','r8')
  # Only the runtime prefix should carry the new forward version.
  text=text.replace('samurai-camera224-r9','samurai-camera224-r9')
 text=text.replace('camera219 full framework','camera224 full framework')
 compile(text,target,'exec');(here/target).write_text(text)
print('K224_FULL_QA_AND_ACTUAL_R8_ROLLBACK_STAGING_PREPARED')
