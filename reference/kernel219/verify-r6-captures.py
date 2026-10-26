"""Run finite native captures, then restore the module's full-mode gate."""
from pathlib import Path
import host,json,subprocess,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1] in ['isolated-r6','installed-r6'];phase=sys.argv[1]
controller=(here/'full-mode-control.py').read_text().replace("out=root/'k219-full-mode-experiment'","out=root/'k219-full-mode-experiment-"+phase+"'")
def control(action):
 p=host.ssh('python3 - '+action,input=controller.encode(),timeout=70)
 (host.PRIVATE/(phase+'-full-mode-'+action+'-host-private.log')).write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);(here/(phase+'-full-mode-'+action+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
def capture(kind,pattern,w,h,cell,config):
 subprocess.run([sys.executable,str(here/'run-r6-capture.py'),phase,kind,str(pattern),str(w),str(h),str(cell),config],check=True,timeout=120)
for kind,pattern,w,h in [('raw',0,2304,1728),('raw',2,2304,1728),('rgb',2,2296,1728),('rgb',0,2296,1728)]:capture(kind,pattern,w,h,1,'default')
control('start')
try:
 for kind,pattern in [('raw',0),('raw',2),('rgb',2),('rgb',0)]:capture(kind,pattern,4608,3456,2,'full')
finally:control('finish')
