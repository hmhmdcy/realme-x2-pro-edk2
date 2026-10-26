from pathlib import Path
import host,json,subprocess,sys

here=Path(__file__).resolve().parent;controller=(here/'full-mode-control.py').read_text()
def control(phase):
    p=host.ssh('python3 - '+phase,input=controller.encode(),timeout=70)
    (host.PRIVATE/('full-mode-'+phase+'-host-private.log')).write_bytes(p.stdout+p.stderr)
    report=json.loads(p.stdout);(here/('full-mode-'+phase+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
control('start')
try:
    for args in [['raw','0','4608','3456','2','system'],['raw','2','4608','3456','2','system'],['rgb','2','4608','3456','2','candidate']]:
        process=subprocess.run([sys.executable,str(here/'run-mode.py')]+args,timeout=120)
        assert process.returncode==0,'Capture failure retained; restore default flag and policy before inspection'
finally:control('finish')
print('Physical full-mode capture experiments completed; default module flag restored')
