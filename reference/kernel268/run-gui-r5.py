from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent
upload="from pathlib import Path;import sys;Path('/var/lib/samurai/k268-tools/gui-auto-r5.py').write_bytes(sys.stdin.buffer.read())"
host.ssh('python3 -c '+shlex.quote(upload),input=(R/'gui-auto-r5.py').read_bytes())
q=host.ssh('python3 -',input=(R/'native-snapshot-gui-r5.py').read_bytes(),timeout=120,check=False);(host.PRIVATE/'snapshot-gui-r5-private.log').write_bytes(q.stdout+q.stderr)
assert q.stdout,'Inspect one-shot GUI state before any retry'
d=json.loads(q.stdout)
for photo in (d.get('gui_control') or {}).get('new_jpegs',[]):photo.pop('path',None)
(R/'snapshot-gui-r5-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(completed=d['diagnostic_completed'],app_exit=d['app_exit_code'],controller_exit=d.get('controller_exit_code'),gui=d.get('gui_control'),fault_delta=d['fault_delta'],cleanup_errors=d['restore_errors']),indent=2))
assert q.returncode==0 and d['diagnostic_completed']

