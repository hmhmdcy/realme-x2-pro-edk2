from pathlib import Path
import difflib,hashlib,json
R=Path(__file__).parent;B=R.parent/'kernel235';p=R/'imx319.c';s=p.read_text();lines=s.splitlines(True)
def indent(n):return '\t'*(n//8)+' '*(n%8)
i=next(i for i,l in enumerate(lines) if l.startswith('static int imx319_get_selection('));n=lines[i].expandtabs(8).index('(')+1
for j in [i+1,i+2]:lines[j]=indent(n)+lines[j].lstrip()
i=next(i for i,l in enumerate(lines) if 'mode = v4l2_find_nearest_size(imx319->profile->modes,' in l and i>2300);n=lines[i].expandtabs(8).index('(')+1
for j in [i+1,i+2,i+3]:lines[j]=indent(n)+lines[j].lstrip()
s=''.join(lines);p.write_text(s)
header='''Subject: [PATCH] media: imx319: report preset crop geometry and camera location

Report analogue crop coordinates from each existing register-list mode.
Expose mounting properties exclusively from firmware. Board location
belongs in the RMX1931 device tree. Keep sensor registers unchanged.
Do not invent an unknown sensor rotation.

---
'''
(R/'imx319-standard-metadata.patch').write_text(header+''.join(difflib.unified_diff((B/'imx319.c').read_text().splitlines(True),s.splitlines(True),fromfile='a/drivers/media/i2c/imx319.c',tofile='b/drivers/media/i2c/imx319.c')))
report=json.loads((R/'source-validation.json').read_text());report['source_sha256']=hashlib.sha256(s.encode()).hexdigest();(R/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(final_source_sha256=report['source_sha256'])))

