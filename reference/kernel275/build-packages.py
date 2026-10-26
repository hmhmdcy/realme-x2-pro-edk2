"""Use the normal complete abuild path, retaining original214 and the r21 cache."""
from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/build-packages.py').read_text()
# Resolve the existing generator first, then substitute the final generated build program.
import ast
tree=ast.parse(source);prefix=source[:source.index("exec(compile(text,")]
ns=dict(__file__=str(R.parent/'kernel273/build-packages.py'));exec(compile(prefix,'resolve273-build.py','exec'),ns);text=ns['text']
for before,after in [("kernel273')","kernel275')"),('libcamera214-before273-r21','libcamera214-before275-r22'),
 ('libcamera273-r21-built','libcamera275-r22-built'),('libcamera271-r20-built','__RETAINED_R21_CACHE__'),
 ('libcamera273-r21','libcamera275-r22'),('samurai-camera-config273-r21','samurai-camera-config275-r22'),
 ('packages273-r21','packages275-r22'),('packages-config273-r21','packages-config275-r22'),
 ("proof['patch_count']==25","proof['patch_count']==26"),('0025-s5kgw1-native-gain-helper.patch','0026-simple-lens-stream-lifetime.patch'),
 ('stage=273','stage=275'),('r21-build-state','r22-build-state'),('r21-patch-apply','r22-patch-apply'),('full-r21-build','full-r22-build'),
 ('r21-package-build-validation','r22-package-build-validation'),('prior24','prior25'),('r20-cache-before','r21-cache-before'),
 ('r20_cache_files','r21_cache_files'),('retained-r20','retained-r21'),('full-feature-r21-build-live','full-feature-r22-build-live'),('config-r16-build','config-r17-build')]:
 assert before in text,before;text=text.replace(before,after)
text=text.replace('__RETAINED_R21_CACHE__','libcamera273-r21-built')
assert "cache=SDK/'work/libcamera273-r21-built'" in text
exec(compile(text,'build-packages275-generated.py','exec'),dict(__file__=str(R/'build-packages.py')))
