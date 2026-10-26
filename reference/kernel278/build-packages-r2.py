"""Fresh full build after the terminal const-interface error; retain all first-attempt evidence."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent;p=R/'build-packages.py';tree=ast.parse(p.read_text());tree.body.pop()
ns=dict(__file__=str(p));exec(compile(tree,'resolve278-build.py','exec'),ns);text=ns['text']
for a,b in [('libcamera214-before278-r24','libcamera214-before278-r24-r2'),('libcamera278-r24-built','libcamera278-r24-r2-built'),
 ('packages278-r24','packages278-r24-r2'),('packages-config278-r24','packages-config278-r24-r2'),
 ('r24-build-state','r24-r2-build-state'),('r24-patch-apply','r24-r2-patch-apply'),('full-r24-build','full-r24-r2-build'),
 ("P/'original214-work-manifest-private.json'","P/'original214-work-r2-manifest-private.json'"),('r23-cache-before-private.json','r23-cache-before-r2-private.json'),
 ('config-r19-build','config-r19-r2-build')]:
 assert a in text,a;text=text.replace(a,b)
exec(compile(text,'build-packages278-r2-generated.py','exec'),dict(__file__=str(R/'build-packages-r2.py')))
