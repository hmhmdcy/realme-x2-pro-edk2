from pathlib import Path
import json,re
here=Path(__file__).resolve().parent
assert json.loads((here/'candidate-native-validation.json').read_text())['raw_only_exposure_gain_metadata_and_automatic_updates_verified']
for flavour in ['candidate-threaded','candidate-isolated']:
 assert json.loads((here/('lifecycle-'+flavour+'-validation.json')).read_text())['all40_requests_completed_or_cancelled']
for source,target in [('native-r7-preflight.py','native-r9-preflight.py'),('install-r7-packages.py','install-r9-packages.py'),('reload-wireplumber.py','reload-wireplumber.py')]:
 text=(here.parent/'kernel220'/source).read_text()
 replacements=dict([('k220-r7','k224-r9'),('k219-r6','k223-r8'),('k220-baseline','k224-baseline'),('stage=220','stage=224'),('0.1.0-r2','0.1.0-r4'),('0.1.0-r1','0.1.0-r3'),('99990.7.2-r7','99990.7.2-r9'),('99990.7.2-r6','99990.7.2-r8'),('r7','r9'),('r6','r8')])
 text=re.sub('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)),lambda m:replacements[m[0]],text)
 compile(text,target,'exec');(here/target).write_text(text)
print('K224_NATIVE_SEVEN_PACKAGE_INSTALL_AND_ACTUAL_R8_ROLLBACK_PREPARED')
