from pathlib import Path
import difflib,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel158');out=Path('/mnt/e/edk2-samurai-out/kernel158')
n='drivers/gpu/drm/msm/msm_drv.h';s=(k/n).read_text();needle='}\nstatic inline int msm_dsi_quiesce_firmware'
assert s.count(needle)==1;(k/n).write_text(s.replace(needle,'}\n\nstatic inline int msm_dsi_quiesce_firmware',1))
report=json.loads((ref/'source-validation.json').read_text());before=json.loads((out/'source-before-private.json').read_text())
patch=(ref/'before-ctl-stop.patch').read_text().split('diff --git',1)[0]
for n in report['modified_files']:
    s=(k/n).read_text();report['after_sha256'][n]=hashlib.sha256(s.encode()).hexdigest()
    patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(before[n].splitlines(True),s.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');(ref/'before-ctl-stop.patch').write_text(patch)
