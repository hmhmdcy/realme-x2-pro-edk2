from pathlib import Path
import json

here=Path(__file__).resolve().parent
text=(here.parent/'kernel224/build-r11-candidate.py').read_text()
replacements={
 'kernel224':'kernel225',
 'libcamera214-before224-r11':'libcamera214-before225',
 'libcamera224-r11-built':'libcamera225-built',
 'libcamera224-r10-built':'libcamera224-r11-built',
 'libcamera224-r11':'libcamera225',
 'packages224-r11':'packages225',
 'packages-config224-r11':'packages-config225',
 'samurai-camera-config224-r11':'samurai-camera-config225',
 'r11-build-state-private.json':'r12-build-state-private.json',
 'r11-patch-apply-private.log':'r12-patch-apply-private.log',
 'full-r11-build-private.log':'full-r12-build-private.log',
 'config-r6-build-private.log':'config-r7-build-private.log',
 'r11-package-build-validation.json':'package-build-validation.json',
 '0017-simple-capture-cancel-status.patch':'0018-simple-manual-exposure-controls.patch',
 'cancel-status-source-validation.json':'candidate-source-validation.json',
 'stage=224':'stage=225',
 'prior16':'prior17',
 'r10_object_cache_preserved':'r11_object_cache_preserved',
 'retained-r10-cache-copy-live':'retained-r11-cache-copy-live',
 'full-feature-r11-build-live':'full-feature-r12-build-live',
 'r11-build-terminal-restoration-pending':'r12-build-terminal-restoration-pending',
 'all13-r11-r6-packages-built-original214-restored':'all13-r12-r7-packages-built-original214-restored',
 }
# One pass prevents replacement outputs being rewritten by later entries.
import re
pattern=re.compile('|'.join(re.escape(k) for k in sorted(replacements,key=len,reverse=True)))
text=pattern.sub(lambda m:replacements[m.group()],text)
assert "cache=root/'work/libcamera224-r11-built'" in text
assert "retained=root/'work/libcamera225-built'" in text
assert '/work/samurai-camera-config225' in text
compile(text,'build-r12-candidate.py','exec');(here/'build-r12-candidate.py').write_text(text)
print('Full r12/r7 build prepared; original tree snapshot/restoration retained.')
