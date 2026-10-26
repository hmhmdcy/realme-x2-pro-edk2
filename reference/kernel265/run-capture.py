"""Launch one fresh bounded standard-camera probe, preserving private evidence."""
from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;which=sys.argv[1];run=int(sys.argv[2]);assert which in ['front','rear'] and run in range(1,19)
snapshot=host.PRIVATE/('inputs-camera-'+str(run));assert not snapshot.exists();snapshot.mkdir()
for name in ['camera-probe.py','native-capture.py']:
 data=(R/name).read_bytes();(snapshot/name).write_bytes(data)
 if name=='native-capture.py':continue
 code="from pathlib import Path;import sys,os,pwd;root=Path('/var/lib/samurai/k265-tools');root.mkdir(mode=0o755,exist_ok=True);p=root/"+repr(name)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644);u=Path('/var/lib/samurai/k265-user');u.mkdir(mode=0o700,exist_ok=True);v=pwd.getpwuid(10000);os.chown(u,v.pw_uid,v.pw_gid)"
 host.ssh('python3 -c '+shlex.quote(code),input=data)
q=host.ssh('python3 - '+which+' '+str(run),input=(snapshot/'native-capture.py').read_bytes(),timeout=120,check=False);(host.PRIVATE/('camera-'+str(run)+'-private.log')).write_bytes(q.stdout+q.stderr)
assert q.stdout,'Inspect phone context before repeating any capture'
d=json.loads(q.stdout);(R/('camera-'+str(run)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');p=d.get('probe_result') or {}
samples=p.get('sampled_preview_frames') or []
print(json.dumps(dict(run=run,camera=which,completed=d['diagnostic_completed'],frames=p.get('buffers'),held_checked=p.get('held_checked'),held_changes=p.get('held_content_changed'),pts_increasing=p.get('pts_strictly_increasing'),caps=p.get('caps'),image_done=p.get('image_done_message'),jpeg_bytes=p.get('saved_jpeg_bytes'),samples_first_and_last=[samples[0],samples[-1]] if samples else [],fault_delta=d.get('fault_delta'),cleanup_errors=d.get('restore_errors')),indent=2))
assert q.returncode==0 and d['diagnostic_completed']
