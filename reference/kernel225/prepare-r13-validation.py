"""Keep the rejected r12 artifacts and prepare distinct r13 validation contexts."""
from pathlib import Path
import re

here=Path(__file__).resolve().parent
source=(here/'prepare-validation.py').read_text()
replacements={
 "'inspect-full-features.py'":"'inspect-r13-full-features.py'",
 "'collect-forward-packages.py'":"'collect-r13-forward-packages.py'",
 "'host-runtime-qa.py'":"'host-r13-runtime-qa.py'",
 "'stage-r12-packages.py'":"'stage-r13-packages.py'",
 "'libcamera224-r11':'libcamera225'":"'libcamera224-r11':'libcamera225-r13'",
 "'samurai-camera-config224-r11':'samurai-camera-config225'":"'samurai-camera-config224-r11':'samurai-camera-config225-r13'",
 "'packages224-r11':'packages225'":"'packages224-r11':'packages225-r13'",
 "'packages-config224-r11':'packages-config225'":"'packages-config224-r11':'packages-config225-r13'",
 "'candidate224-r11':'candidate225'":"'candidate224-r11':'candidate225-r13'",
 'samurai-camera225-r12':'samurai-camera225-r13','k225-r12':'k225-r13',
 "'camera-forward-repo-r11':'camera-forward-repo'":"'camera-forward-repo-r11':'camera-forward-repo-r13'",
 "'camera-selected-repo-r11':'camera-selected-repo'":"'camera-selected-repo-r11':'camera-selected-repo-r13'",
 "'r11-package-build-validation.json':'package-build-validation.json'":"'r11-package-build-validation.json':'r13-package-build-validation.json'",
 "'r11-full-feature-configuration-validation.json':'full-feature-configuration-validation.json'":"'r11-full-feature-configuration-validation.json':'r13-full-feature-configuration-validation.json'",
 "'r11-forward-package-artifact-validation.json':'forward-package-artifact-validation.json'":"'r11-forward-package-artifact-validation.json':'r13-forward-package-artifact-validation.json'",
 "'r11-host-runtime-qa-validation.json':'host-runtime-qa-validation.json'":"'r11-host-runtime-qa-validation.json':'r13-host-runtime-qa-validation.json'",
 "'r11-staging-validation.json':'staging-validation.json'":"'r11-staging-validation.json':'r13-staging-validation.json'",
 "'r11-bundle':'r12-bundle'":"'r11-bundle':'r13-bundle'",
 "'r11-candidate-bundle':'r12-candidate-bundle'":"'r11-candidate-bundle':'r13-candidate-bundle'",
 "'r11-transfer-offset':'r12-transfer-offset'":"'r11-transfer-offset':'r13-transfer-offset'",
 "'99990.7.2-r11':'99990.7.2-r12'":"'99990.7.2-r11':'99990.7.2-r13'",
 "'0.1.0-r6':'0.1.0-r7'":"'0.1.0-r6':'0.1.0-r8'",
 'upstream_verifier_uses_current_r12_core_and_base':'upstream_verifier_uses_current_r13_core_and_base',
 }
pattern=re.compile('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)));source=pattern.sub(lambda m:replacements[m.group()],source)
exec(compile(source,'separate-r13-qa-generation','exec'))
text=(here/'build-agc-regression.py').read_text().replace('package-build-validation.json','r13-package-build-validation.json').replace('libcamera225-built','libcamera225-r13-built').replace('agc-control-regression225','agc-control-regression225-r13').replace('agc-control-regression-validation.json','r13-agc-control-regression-validation.json').replace('agc-regression-','r13-agc-regression-')
(here/'build-r13-agc-regression.py').write_text(text)
text=(here/'build-manual-probe.py').read_text().replace('host-runtime-qa-validation.json','r13-host-runtime-qa-validation.json').replace('/candidate225/','/candidate225-r13/').replace('manual-control-probe225','manual-control-probe225-r13').replace("private/'manual-control-probe'","private/'manual-control-probe-r13'").replace('/samurai-camera225-probes/manual-control-probe','/samurai-camera225-probes/manual-control-probe-r13').replace('manual-probe-build-validation.json','r13-manual-probe-build-validation.json').replace('manual-probe-build-private.log','r13-manual-probe-build-private.log')
(here/'build-r13-manual-probe.py').write_text(text)
text=(here/'native-manual-runner.py').read_text().replace('samurai-camera225-r12','samurai-camera225-r13').replace("tag=f'manual-controls-","tag=f'manual-controls-r13-").replace('/samurai-camera225-probes/manual-control-probe','/samurai-camera225-probes/manual-control-probe-r13')
(here/'native-r13-manual-runner.py').write_text(text)
text=(here/'run-manual-case.py').read_text().replace('staging-validation.json','r13-staging-validation.json').replace('agc-control-regression-validation.json','r13-agc-control-regression-validation.json').replace('native-manual-runner.py','native-r13-manual-runner.py').replace('manual-controls-','manual-controls-r13-').replace('99990.7.2-r12','99990.7.2-r13')
text=text.replace("label=f'{kind}","label=f'r13-{kind}")
# The native context tag is generated independently and does not include label.
(here/'run-r13-manual-case.py').write_text(text)
for p in here.glob('*r13*.py'):compile(p.read_text(),str(p),'exec')
print('Distinct r13/r8 QA, algorithm regression, probe and native cases prepared; no native capture performed.')
