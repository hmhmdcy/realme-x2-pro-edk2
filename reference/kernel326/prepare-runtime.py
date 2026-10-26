from pathlib import Path
import io,json,sys,tarfile
import host
HERE=Path(__file__).resolve().parent
plan=HERE/(sys.argv[1] if len(sys.argv)>1 else 'read-plan-validation.json')
plans=json.loads(plan.read_text());assert plans['passed']
files={'worker.py':HERE/'native-read.py','plans.json':plan,'pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture'}
with tarfile.open(host.PRIVATE/'read.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
print('Prepared standard cam power ownership and '+str(len(plans['plans']))+' read-only EEPROM maps; no new binaries.')
