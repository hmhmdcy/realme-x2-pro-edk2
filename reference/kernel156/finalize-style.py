from pathlib import Path
import difflib,hashlib,json,textwrap
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
report=json.loads((ref/'source-validation.json').read_text())
before=json.loads((out/'source-before-private.json').read_text())
for n,sha in report['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
p=k/'drivers/gpu/drm/drm_panel.c';s=p.read_text()
old='''\telse
		trace_drm_panel_backlight(dev_name(panel->dev), 0,
					  panel->backlight ? panel->backlight->props.brightness : -1);'''
assert s.count(old)==1
s=s.replace(old,'''\telse {
		int brightness = panel->backlight ? panel->backlight->props.brightness : -1;

		trace_drm_panel_backlight(dev_name(panel->dev), 0, brightness);
	}''',1)
p.write_text(s)
patch=ref/'first-frame-backlight.patch'
header=patch.read_text().split('\n---\n',1)[0]
subject,body=header.split('\n\n',1)
header=subject+'\n\n'+textwrap.fill(' '.join(body.split()),width=72)+'\n\n---\n\n'
diffs=[];stats=[];total_add=total_del=0
for n in report['modified_files']:
    current=(k/n).read_text()
    diff=''.join(difflib.unified_diff((before[n] or '').splitlines(True),current.splitlines(True),fromfile='/dev/null' if before[n] is None else 'a/'+n,tofile='b/'+n))
    adds=sum(line.startswith('+') and not line.startswith('+++') for line in diff.splitlines())
    dels=sum(line.startswith('-') and not line.startswith('---') for line in diff.splitlines())
    total_add+=adds;total_del+=dels
    stats.append(f' {n} | {adds+dels} '+('+' if adds else '')+('-' if dels else '')+'\n')
    diffs.append('diff --git a/'+n+' b/'+n+'\n'+('new file mode 100644\n' if before[n] is None else '')+diff)
    report['after_sha256'][n]=hashlib.sha256(current.encode()).hexdigest()
patch.write_text(header+''.join(stats)+f' {len(diffs)} files changed, {total_add} insertions(+), {total_del} deletions(-)\n\n'+''.join(diffs))
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K156_SOURCE_STYLE_FINALIZED')
