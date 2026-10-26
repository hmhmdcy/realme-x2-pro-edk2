"""Revalidate four physical modes; keep pre-fix reports and restore default."""
from pathlib import Path
import host,json,subprocess,sys

here=Path(__file__).resolve().parent
controller=(here/'full-mode-control.py').read_text().replace("out=root/'k219-full-mode-experiment'","out=root/'k219-full-mode-experiment-r4'")
def control(phase):
    p=host.ssh('python3 - '+phase,input=controller.encode(),timeout=70)
    (host.PRIVATE/('full-mode-r4-'+phase+'-host-private.log')).write_bytes(p.stdout+p.stderr)
    report=json.loads(p.stdout);(here/('full-mode-r4-'+phase+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
def measure(w,h,v):
    subprocess.run([sys.executable,str(here/'measure-mode-timing.py'),str(w),str(h),str(v),'after-timing-fix'],check=True,timeout=120)
for w,h,v in [(1928,1088,-1),(2304,1728,-1),(2304,1728,396)]:measure(w,h,v)
control('start')
try:measure(4608,3456,-1)
finally:control('finish')
