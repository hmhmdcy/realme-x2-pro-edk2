"""Measure actual constant probe output and verify all diagnostics have terminated."""
from pathlib import Path
import hashlib,json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai/k289-cst-r1');images={}
for label,suffix in [('high','corrected'),('low','offset-low')]:
 b=(root/('first-nv12-private.raw.'+suffix)).read_bytes();assert len(b)==115200
 def stats(data):return dict(min=min(data),max=max(data),mean=sum(data)/len(data),unique_values=len(set(data)))
 images[label]=dict(sha256=hashlib.sha256(b).hexdigest(),y=stats(b[:76800]),u=stats(b[76800::2]),v=stats(b[76801::2]))
workers=[]
for name in ['k289-dmi-r1','k289-dmi-r2','k289-baseline-r1','k289-dmi-r3','k289-dmi-r4','k289-dmi-r5','k289-gamma-r1','k289-cst-r1']:
 s=json.loads(Path('/var/lib/samurai',name,'state-private.json').read_text());pid=s['pid'];exists=Path('/proc',str(pid)).exists()
 assert s['terminal'] and not exists;workers.append(dict(name=name,terminal=True,process_gone=True,exit_code=s['exit_code']))
print(json.dumps(dict(stage=289,images=images,workers=workers,cst_offset_semantics_not_resolved=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
report=json.loads(q.stdout);(ROOT/'constant-pixel-and-workers-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
# Reuse the current coherent deployment inventory checks without changing the old receipt.
s=(ROOT.parent/'kernel288/final-health.py').read_text()
s=s.replace("assert json.loads((ROOT/'four-camera-regression-validation.json').read_text())['passed']", "assert json.loads((ROOT.parent/'kernel288/four-camera-regression-validation.json').read_text())['passed']")
s=s.replace("(ROOT/'tpg-r3-validation.json')", "(ROOT.parent/'kernel288/tpg-r3-validation.json')")
s=s.replace('dict(stage=288','dict(stage=289')
exec(compile(s,'kernel288-deployment-health','exec'),globals())
