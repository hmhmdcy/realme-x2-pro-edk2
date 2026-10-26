"""Reuse the full abuild workflow with an isolated r23 candidate and preserved r22 cache."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent
source=(R.parent/'kernel275/build-packages.py').read_text()
tree=ast.parse(source)
assert isinstance(tree.body[-1],ast.Expr) and isinstance(tree.body[-1].value,ast.Call) and tree.body[-1].value.func.id=='exec'
tree.body.pop()
ns=dict(__file__=str(R.parent/'kernel275/build-packages.py'));exec(compile(tree,'resolve275-build.py','exec'),ns);text=ns['text']
for before,after in [("kernel275')","kernel277')"),('libcamera214-before275-r22','libcamera214-before277-r23'),
 ('libcamera275-r22-built','libcamera277-r23-built'),('libcamera273-r21-built','__KEEP_R22_CACHE__'),
 ('libcamera275-r22','libcamera277-r23'),('samurai-camera-config275-r22','samurai-camera-config277-r23'),
 ('packages275-r22','packages277-r23'),('packages-config275-r22','packages-config277-r23'),
 ("proof['patch_count']==26","proof['patch_count']==27"),('0026-simple-lens-stream-lifetime.patch','0027-softisp-raw-focus-statistics.patch'),
 ('stage=275','stage=277'),('r22-build-state','r23-build-state'),('r22-patch-apply','r23-patch-apply'),
 ('full-r22-build','full-r23-build'),('r22-package-build-validation','r23-package-build-validation'),
 ('prior25','prior26'),('r21-cache-before','r22-cache-before'),('r21_cache_files','r22_cache_files'),
 ('retained-r21','retained-r22'),('full-feature-r22-build-live','full-feature-r23-build-live'),('config-r17-build','config-r18-build')]:
 assert before in text,before;text=text.replace(before,after)
text=text.replace('__KEEP_R22_CACHE__','libcamera275-r22-built')
assert "cache=SDK/'work/libcamera275-r22-built'" in text
exec(compile(text,'build-packages277-generated.py','exec'),dict(__file__=str(R/'build-packages.py')))
