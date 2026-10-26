from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=int(sys.argv[1]);assert mode in [6000091,6000092,6000093,6000101,6000111,6000121,6000131,6000132,6000133,6000141,6000142,6000143,6000151,6000152,6000153,6000154]
snapshot=host.PRIVATE/('inputs-compat-'+str(mode));assert not snapshot.exists();snapshot.mkdir()
for name in ['compat-runner.py','compat-probe.py','select-front.py','native-compat.py']:
 data=(R/name).read_bytes();(snapshot/name).write_bytes(data)
 if name=='native-compat.py':continue
 code="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k265-compat-tools');p.mkdir(mode=0o755,exist_ok=True);p=p/"+repr(name)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(code),input=data)
q=host.ssh('python3 - '+str(mode),input=(snapshot/'native-compat.py').read_bytes(),timeout=120,check=False);(host.PRIVATE/('compat-'+str(mode)+'-private.log')).write_bytes(q.stdout+q.stderr)
assert q.stdout,'Inspect one-shot phone context before retry'
d=json.loads(q.stdout);(R/('compat-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');p=d.get('probe_result') or {}
print(json.dumps(dict(mode=mode,completed=d['diagnostic_completed'],failure=p.get('failure'),clients=[{k:r.get(k) for k in ['label','buffers','held_checked','held_content_changed','pts_span_seconds','not_recycled_errors']} for r in p.get('clients',[])],fault_delta=d.get('fault_delta'),cleanup_errors=d.get('restore_errors')),indent=2))
assert q.returncode==0 and d['diagnostic_completed']

