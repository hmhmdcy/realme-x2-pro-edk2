from pathlib import Path
import json
here=Path(__file__).resolve().parent
assert json.loads((here/'r10-package-build-validation.json').read_text())['framework_and_config_packages_built']
for old,new in [('inspect-full-features.py','inspect-r10-full-features.py'),('collect-forward-packages.py','collect-r10-forward-packages.py'),('host-runtime-qa.py','host-r10-runtime-qa.py'),('stage-r9-packages.py','stage-r10-packages.py')]:
 text=(here/old).read_text()
 for a,b in [('libcamera224-built','libcamera224-r10-built'),('packages224','packages224-r10'),('packages-config224','packages-config224-r10'),('samurai-camera-config224','samurai-camera-config224-r10'),('libcamera224-qa-prefix','libcamera224-r10-qa-prefix'),('camera-forward-repo','camera-forward-repo-r10'),('camera-selected-repo','camera-selected-repo-r10'),('candidate224','candidate224-r10'),('/tmp/k224-runtime','/tmp/k224-r10-runtime'),('r9','r10'),('0.1.0-r4','0.1.0-r5'),('package-build-validation.json','r10-package-build-validation.json'),('full-feature-configuration-validation.json','r10-full-feature-configuration-validation.json'),('forward-package-artifact-validation.json','r10-forward-package-artifact-validation.json'),('host-runtime-qa-validation.json','r10-host-runtime-qa-validation.json')]:text=text.replace(a,b)
 text=text.replace("root/'tmp/k224-runtime'","root/'tmp/k224-r10-runtime'")
 compile(text,new,'exec');(here/new).write_text(text)
text=(here/'run-candidate-checks.py').read_text().replace('r9','r10')
text=text.replace("(label+'-candidate-host-private.log')","('r10-'+label+'-candidate-host-private.log')").replace("(label+'-candidate-validation.json')","('r10-'+label+'-candidate-validation.json')").replace("here/'candidate-native-validation.json'","here/'r10-candidate-native-validation.json'")
text=text.replace('report=dict(stage=224,case=',"report=dict(stage=224,framework='99990.7.2-r10',case=")
compile(text,'r10-candidate-checks','exec');(here/'run-r10-candidate-checks.py').write_text(text)
text=(here/'run-lifecycle.py').read_text().replace("here/'candidate-native-validation.json'","here/'r10-candidate-native-validation.json'").replace('samurai-camera224-r9','samurai-camera224-r10').replace("repr('lifecycle-'+flavour+'-r2')","repr('lifecycle-r10-'+flavour+'-r2')").replace("('lifecycle-'+flavour+'-host-private.log')","('lifecycle-r10-'+flavour+'-host-private.log')").replace("('lifecycle-'+flavour+'-validation.json')","('lifecycle-r10-'+flavour+'-validation.json')").replace("['new_r9_camera_libraries_loaded']","['new_r10_camera_libraries_loaded']")
text=text.replace('report=dict(stage=224,flavour=',"report=dict(stage=224,framework='99990.7.2-r10',flavour=")
compile(text,'r10-lifecycle-check','exec');(here/'run-r10-lifecycle.py').write_text(text)
print('K224_R10_SEPARATE_QA_REPOSITORY_PREFIX_AND_UNCHANGED_LIFECYCLE_PROBE_PREPARED')
