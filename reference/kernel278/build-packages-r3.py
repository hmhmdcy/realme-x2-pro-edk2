"""Full normal packaging from verified r2 cache plus a two-file corrected source delta."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent;p=R/'build-packages.py';tree=ast.parse(p.read_text());tree.body.pop()
ns=dict(__file__=str(p));exec(compile(tree,'resolve278-build.py','exec'),ns);text=ns['text']
for a,b in [('libcamera214-before278-r24','libcamera214-before278-r24-r3'),('libcamera278-r24-built','libcamera278-r24-r3-built'),
 ('libcamera277-r23-built','libcamera278-r24-r2-built'),('packages278-r24','packages278-r24-r3'),('packages-config278-r24','packages-config278-r24-r3'),
 ('r24-build-state','r24-r3-build-state'),('r24-patch-apply','r24-r3-patch-apply'),('full-r24-build','full-r24-r3-build'),
 ("P/'original214-work-manifest-private.json'","P/'original214-work-r3-manifest-private.json'"),('r23-cache-before-private.json','r24-r2-cache-before-r3-private.json'),
 ('r23_cache_files_unchanged','r24_r2_cache_files_unchanged'),('retained-r23','retained-r24-r2'),('config-r19-build','config-r19-r3-build'),
 ("str(work/'0028-simple-contrast-autofocus.patch')","str(R/'af-r2-to-r3.patch')")]:
 assert a in text,a;text=text.replace(a,b)
exec(compile(text,'build-packages278-r3-generated.py','exec'),dict(__file__=str(R/'build-packages-r3.py')))
