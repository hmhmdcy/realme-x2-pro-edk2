from pathlib import Path
import difflib,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
report=json.loads((ref/'source-validation.json').read_text())
before=json.loads((out/'source-before-private.json').read_text())
for n,sha in report['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
p=k/'drivers/gpu/drm/drm_panel.c';s=p.read_text()
old='\tpanel->connector_type = connector_type;'
assert s.count(old)==1
s=s.replace(old,old+'\n\tpanel->delay_backlight_until_first_frame = false;\n\tpanel->backlight_ready = false;',1)
p.write_text(s)
patch=ref/'first-frame-backlight.patch'
text=patch.read_text().split('diff --git ',1)[0]
for n in report['modified_files']:
    current=(k/n).read_text()
    text+='diff --git a/'+n+' b/'+n+'\n'
    if before[n] is None:text+='new file mode 100644\n'
    text+=''.join(difflib.unified_diff((before[n] or '').splitlines(True),current.splitlines(True),fromfile='/dev/null' if before[n] is None else 'a/'+n,tofile='b/'+n))
    report['after_sha256'][n]=hashlib.sha256(current.encode()).hexdigest()
patch.write_text(text)
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K156_INIT_DEFAULTS_EXPLICIT')
