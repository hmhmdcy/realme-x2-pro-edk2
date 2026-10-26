from pathlib import Path
import json
here=Path(__file__).resolve().parent
assert json.loads((here/'r11-package-build-validation.json').read_text())['framework_and_config_packages_built']
names=[('inspect-r10-full-features.py','inspect-r11-full-features.py'),('collect-r10-forward-packages.py','collect-r11-forward-packages.py'),('host-r10-runtime-qa.py','host-r11-runtime-qa.py'),('stage-r10-packages.py','stage-r11-packages.py'),('run-r10-candidate-checks.py','run-r11-candidate-checks.py'),('run-r10-lifecycle.py','run-r11-lifecycle.py')]
for source,target in names:
 text=(here/source).read_text().replace('r10','r11').replace('0.1.0-r5','0.1.0-r6')
 text=text.replace("root/'tmp/k224-runtime'","root/'tmp/k224-r11-runtime'")
 if target=='run-r11-lifecycle.py':
  text=text.replace("here/'r11-candidate-native-validation.json'","here/'r11-staging-validation.json'").replace("['raw_only_exposure_gain_metadata_and_automatic_updates_verified']","['isolated_full_feature_runtime_staged']")
 compile(text,target,'exec');(here/target).write_text(text)
text=(here/'prepare-package-install.py').read_text().replace("here/'candidate-native-validation.json'","here/'r11-candidate-native-validation.json'").replace("here/('lifecycle-'+flavour+'-validation.json')","here/('lifecycle-r11-'+flavour+'-validation.json')").replace('r9','r11').replace('0.1.0-r4','0.1.0-r6')
compile(text,'prepare-r11-install','exec');(here/'prepare-r11-package-install.py').write_text(text)
print('K224_R11_SEPARATE_QA_AND_UNCHANGED_LIFECYCLE_PROGRAM_PREPARED')
