from pathlib import Path
import host,json,subprocess,sys
here=Path(__file__).resolve().parent
for flavour in ['candidate-threaded','candidate-isolated']:
 for w,h in [(1920,1088),(2296,1728)]:subprocess.run([sys.executable,str(here/'capture-exposure-metadata.py'),str(w),str(h),flavour],check=True,timeout=100)
controller=(here.parent/'kernel219/full-mode-control.py').read_text().replace('stage=219','stage=220')
controller=controller.replace("k219-runtime/boot-id-private.txt","k220-baseline/boot-id-private.txt").replace("out=root/'k219-full-mode-experiment'","out=root/'k220-candidate-full-metadata'")
def control(action):
 p=host.ssh('python3 - '+action,input=controller.encode(),timeout=70)
 (host.PRIVATE/('candidate-full-'+action+'-host-private.log')).write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);(here/('candidate-full-'+action+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
control('start')
try:subprocess.run([sys.executable,str(here/'capture-exposure-metadata.py'),'4608','3456','candidate-threaded'],check=True,timeout=100)
finally:control('finish')
