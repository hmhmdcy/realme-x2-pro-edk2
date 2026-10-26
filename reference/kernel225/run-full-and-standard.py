from pathlib import Path
import host,json,subprocess,sys
here=Path(__file__).resolve().parent
def control(action):
 p=host.ssh('python3 - '+action,input=(here/'native-full-mode-control.py').read_bytes(),timeout=65)
 (host.PRIVATE/('full-'+action+'-host-private.log')).write_bytes(p.stdout+p.stderr)
 r=json.loads(p.stdout);(here/('full-'+action+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
control('start')
try:
 for kind in ['raw','rgb']:subprocess.run([sys.executable,str(here/('capture-full-'+kind+'-metadata.py')),'4608','3456','system-r13'],check=True,timeout=110)
finally:control('finish')
for client in ['cam','gstreamer']:subprocess.run([sys.executable,str(here/'run-standard-r13-client.py'),client],check=True,timeout=110)
