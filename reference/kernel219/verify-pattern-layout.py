from pathlib import Path
import host,json,subprocess,sys
here=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(here/'run-pattern-layout.py'),'2304','1728'],check=True,timeout=120)
controller=(here/'full-mode-control.py').read_text().replace("out=root/'k219-full-mode-experiment'","out=root/'k219-full-mode-experiment-pattern-layout'")
def control(action):
 p=host.ssh('python3 - '+action,input=controller.encode(),timeout=70)
 (host.PRIVATE/('pattern-layout-full-'+action+'-host-private.log')).write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);(here/('pattern-layout-full-'+action+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
control('start')
try:subprocess.run([sys.executable,str(here/'run-pattern-layout.py'),'4608','3456'],check=True,timeout=120)
finally:control('finish')
