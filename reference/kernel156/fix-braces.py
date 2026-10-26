from pathlib import Path
import hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
report=json.loads((ref/'source-validation.json').read_text())
before=json.loads((out/'source-before-private.json').read_text())
for n,sha in report['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
p=k/'drivers/gpu/drm/drm_panel.c';s=p.read_text()
old='\tif (panel->backlight_ready)\n\t\tdrm_panel_enable_backlight(panel);\n\telse {'
assert s.count(old)==1
s=s.replace(old,'\tif (panel->backlight_ready) {\n\t\tdrm_panel_enable_backlight(panel);\n\t} else {',1)
p.write_text(s)
code=(ref/'finalize-style.py').read_text()
import difflib,textwrap
exec(compile(code[code.index("patch=ref/'first-frame-backlight.patch'"):],str(ref/'finalize-style.py'),'exec'))
