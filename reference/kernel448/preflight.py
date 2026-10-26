from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel441/preflight.py').read_text().replace('stage=441','stage=448').replace('k441-adopted','k448-adopted')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
q=host.ssh('python3 -c '+shlex.quote((HERE/'charging-snapshot.py').read_text()),timeout=20);q.check_returncode();charging=json.loads(q.stdout)
(P/'charging-baseline-private.json').write_bytes(q.stdout)
r=json.loads((HERE/'preflight-validation.json').read_text());r.update(new_dt_charging_service_and_three_resident_modules_preserved_as_baseline=True)
(HERE/'preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n')
