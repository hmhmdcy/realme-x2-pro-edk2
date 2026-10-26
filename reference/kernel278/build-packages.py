"""Full signed r24 build while preserving the deployed r23 source cache and original SDK."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent;path=R.parent/'kernel277/build-packages.py';tree=ast.parse(path.read_text());assert isinstance(tree.body[-1],ast.Expr);tree.body.pop()
ns=dict(__file__=str(path));exec(compile(tree,'resolve277-build.py','exec'),ns);text=ns['text']
for a,b in [("kernel277')","kernel278')"),('libcamera214-before277-r23','libcamera214-before278-r24'),
 ('libcamera277-r23-built','libcamera278-r24-built'),('libcamera275-r22-built','__KEEP_R23_CACHE__'),
 ('libcamera277-r23','libcamera278-r24'),('samurai-camera-config277-r23','samurai-camera-config278-r24'),
 ('packages277-r23','packages278-r24'),('packages-config277-r23','packages-config278-r24'),
 ("proof['patch_count']==27","proof['patch_count']==28"),('0027-softisp-raw-focus-statistics.patch','0028-simple-contrast-autofocus.patch'),
 ('stage=277','stage=278'),('r23-build-state','r24-build-state'),('r23-patch-apply','r24-patch-apply'),('full-r23-build','full-r24-build'),
 ('r23-package-build-validation','r24-package-build-validation'),('prior26','prior27'),('r22-cache-before','r23-cache-before'),('r22_cache_files','r23_cache_files'),
 ('retained-r22','retained-r23'),('full-feature-r23-build-live','full-feature-r24-build-live'),('config-r18-build','config-r19-build')]:
 assert a in text,a;text=text.replace(a,b)
text=text.replace('__KEEP_R23_CACHE__','libcamera277-r23-built');assert "cache=SDK/'work/libcamera277-r23-built'" in text
exec(compile(text,'build-packages278-generated.py','exec'),dict(__file__=str(R/'build-packages.py')))
