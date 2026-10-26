"""Full signed r19/r14 using the retained r15 source/objects; restore original SDK."""
from pathlib import Path
import json

R=Path(__file__).resolve().parent
proof=json.loads((R/'source-validation.json').read_text())
assert json.loads((R/'link-test-validation.json').read_text())['asan_ubsan']
text=(R.parent/'kernel239/build-r15.py').read_text()
replacements=[
 ("kernel239')","kernel268')"),
 ('libcamera214-before239-r15','libcamera214-before268-r19'),
 ('libcamera239-r15-built','libcamera268-r19-built'),
 ('libcamera238-r14-built','libcamera239-r15-built'),
 ('libcamera239-r15','libcamera268-r19'),
 ('samurai-camera-config239-r15','samurai-camera-config268-r19'),
 ('packages239-r15','packages268-r19'),('packages-config239-r15','packages-config268-r19'),
 ('r15-source-validation.json','build-source-validation.json'),
 ("proof['patch_count']==22","proof['patch_count']==23"),
 ('0022-soft-initial-parameters.patch','0023-simple-link-state-after-external-client.patch'),
 ('stage=239','stage=268'),('before239','before268'),
 ('r15-build-state','r19-build-state'),('r15-patch-apply','r19-patch-apply'),
 ('full-r15-build','full-r19-build'),('r15-package-build-validation','r19-package-build-validation'),
 ('prior21','prior22'),('stage239','stage268')]
for a,b in replacements:text=text.replace(a,b)
# Sequential string replacements also affect the retained cache; restore its
# exact historical path explicitly rather than building on an untested cache.
start="cache=SDK/'work/libcamera268-r19-built'"
assert text.count(start)==1;text=text.replace(start,"cache=SDK/'work/libcamera239-r15-built'")
text=text.replace('full_feature_targets_and_prior21_patches_retained','full_feature_targets_and_prior22_patches_retained')
buildproof=dict(patch_count=23,
 source_before_files={'src/libcamera/pipeline/simple/simple.cpp':proof['source_before_sha256']},
 source_files={'src/libcamera/pipeline/simple/simple.cpp':proof['source_sha256']})
(R/'build-source-validation.json').write_text(json.dumps(buildproof,indent=2)+'\n')
compile(text,'build-r19-generated.py','exec')
private=Path('/mnt/e/edk2-samurai-out/kernel268')
(private/'generated-build-r19-private.py').write_text(text)
exec(compile(text,'build-r19-generated.py','exec'),dict(__file__=str(R/'build-r19-generated.py')))
