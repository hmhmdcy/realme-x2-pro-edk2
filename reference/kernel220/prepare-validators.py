"""Retain full artifact checks and adjust only version/path provenance."""
from pathlib import Path
here=Path(__file__).resolve().parent;prior=here.parent/'kernel219'
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','stage-r6-packages.py']:
 code=(prior/name).read_text().replace('stage=219','stage=220').replace('/mnt/e/edk2-samurai-out/kernel219','/mnt/e/edk2-samurai-out/kernel220')
 code=code.replace('libcamera219-qa-prefix','libcamera220-qa-prefix').replace('candidate219','candidate220')
 code=code.replace('work/libcamera219/src/','work/libcamera220-built/src/')
 code=code.replace("root/'packages219'","root/'packages220'").replace("root/'packages-config219'","root/'packages-config220'")
 code=code.replace("here/'r6-package-build-validation.json'","here/'package-build-validation.json'").replace("['framework_and_device_config_packages_built']","['framework_and_config_packages_built']")
 code=code.replace('99990.7.2-r6','99990.7.2-r7').replace('0.1.0-r1','0.1.0-r2')
 code=code.replace('samurai-camera-config219','samurai-camera-config220')
 code=code.replace('/tmp/k219-runtime','/tmp/k220-runtime').replace("root/'tmp/k219-runtime'","root/'tmp/k220-runtime'")
 if name=='host-runtime-qa.py':
  code=code.replace('/work/libcamera/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify','/work/libcamera220-built/src/libcamera-v0.7.2/output/src/apps/ipa-verify/ipa_verify')
  code=code.replace('retained_upstream_verifier_uses_current_r6_core_and_base','upstream_verifier_uses_current_r7_core_and_base')
 if name=='stage-r6-packages.py':
  code=code.replace("root/'k219-runtime/boot-id-private.txt'","root/'k220-baseline/boot-id-private.txt'")
  code=code.replace("root/'k219-baseline/installed-before-private.txt'","root/'k220-baseline/installed-before-private.txt'")
  code=code.replace('k219-r6-package-candidates','k220-r7-package-candidates').replace('samurai-camera219-r6','samurai-camera220-r7')
  code=code.replace('r6-', 'r7-')
  code=code.replace("rollback=root/'k214-package-candidates'","rollback=root/'k219-r6-package-candidates'")
  code=code.replace("'0.1.0-r0'", "'0.1.0-r1'").replace("'99990.7.2-r5'", "'99990.7.2-r6'")
  code=code.replace('actual_seven_r5_rollback','actual_seven_r6_rollback')
  code=code.replace("add('bundle-manifest-private.json'", "add('candidate/config-isolated/libcamera/configuration.yaml',yaml.replace(b'configuration:\\n',b'configuration:\\n  ipa:\\n    force_isolation: true\\n'),0o644)\n add('bundle-manifest-private.json'")
  name='stage-r7-packages.py'
 compile(code,name,'exec');(here/name).write_text(code)
print('Complete r7 artifact, IPA/core, retained-feature and native staging validators prepared')
