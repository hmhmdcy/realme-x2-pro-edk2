from pathlib import Path
import difflib,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
out=Path('/mnt/e/edk2-samurai-out/kernel154')
name='drivers/gpu/drm/msm/dsi/dsi_host.c'
p=k/name
s=p.read_text()
assert hashlib.sha256(s.encode()).hexdigest()=='148ae32ff89d102cdee6a314124e9f8e8fc3b62c10ab4ec28b8541d43891c767'
old='\tdsi_ctrl_disable(msm_host);\n\twmb();\n\n\tdsi_timing_setup'
assert s.count(old)==1
s=s.replace(old,'\tdsi_ctrl_disable(msm_host);\n\twmb(); /* Stop the inherited engine before changing its stream timing. */\n\n\tdsi_timing_setup',1)
p.write_text(s)
patch=ref/'host-init.patch'
header=patch.read_text().split('diff --git ',1)[0]
before=(out/'dsi-before153-private.c').read_text()
patch.write_text(header+'diff --git a/'+name+' b/'+name+'\n'+''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
report=json.loads((ref/'source-validation.json').read_text())
report['candidate_sha256']=hashlib.sha256(s.encode()).hexdigest()
(ref/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
