from pathlib import Path
import host,json,subprocess,sys

here=Path(__file__).resolve().parent
controller=(here/'full-mode-control.py').read_text().replace("out=root/'k219-full-mode-experiment'","out=root/'k219-full-mode-experiment-r3'")
def control(phase):
    p=host.ssh('python3 - '+phase,input=controller.encode(),timeout=70)
    (host.PRIVATE/('full-mode-r3-'+phase+'-host-private.log')).write_bytes(p.stdout+p.stderr)
    report=json.loads(p.stdout);(here/('full-mode-r3-'+phase+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
control('start')
try:
    subprocess.run([sys.executable,str(here/'run-mode.py'),'rgb','0','4608','3456','2','candidate'],check=True,timeout=120)
    subprocess.run([sys.executable,str(here/'measure-mode-timing.py'),'4608','3456','-1'],check=True,timeout=120)
finally:control('finish')
