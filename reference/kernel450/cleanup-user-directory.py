"""Remove the exact ended r2 user payload after its observer failure."""
from pathlib import Path
import json,shlex
import host
code=r'''from pathlib import Path
import json,shutil
transaction=Path('/var/lib/samurai/k450-stats-retirement-r2')
state=json.loads((transaction/'state.json').read_text());assert state['terminal'] and state['formal_modules_restored'] and state['services_restored']
target=Path('/run/user/10000/k450-user-r2-user-cancel-1080')
assert not target.is_symlink() and target.resolve().parent==Path('/run/user/10000').resolve() and target.stat().st_uid==10000
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=[arg.decode() for arg in (p/'cmdline').read_bytes().split(bytes([0])) if arg]
  assert not any(arg==str(target) or arg.startswith(str(target)+'/') for arg in args)
 except OSError:pass
assert not any((target/'captures').iterdir())
shutil.rmtree(target);assert not target.exists()
print(json.dumps(dict(exact_ended_r2_payload_removed=True,no_live_process_using_payload=True,private_captures_empty=True,passed=True)))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();data=json.loads(q.stdout)
(host.PRIVATE/'directory-cleanup-r2-private.json').write_bytes(q.stdout)
data['stage']=450;(Path(__file__).resolve().parent/'directory-cleanup-validation.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data))
