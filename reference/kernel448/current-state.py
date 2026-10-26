from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel441/current-state.py').read_text().replace('stage=441','stage=448')
exec(compile(source,str(HERE/'current-state.py'),'exec'))
q=host.ssh('python3 -c '+shlex.quote((HERE/'charging-snapshot.py').read_text()),timeout=20);q.check_returncode();charging=json.loads(q.stdout)
assert charging==json.loads((P/'charging-baseline-private.json').read_text())
(P/'charging-after-private.json').write_bytes(q.stdout)
r=json.loads((HERE/'current-state-validation.json').read_text());r.update(persistent_charging_modules_limits_native_budget_and_boot_enable_unchanged=True)
(HERE/'current-state-validation.json').write_text(json.dumps(r,indent=2)+'\n')
