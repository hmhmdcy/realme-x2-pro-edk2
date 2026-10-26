"""Copy only the generated physical-sensor test-pattern JPEG for visual QA."""
from pathlib import Path
import hashlib,json,shlex
import host
d=json.loads((host.PRIVATE/'telephoto-bars-response-private.log').read_text());row=d['photo']
assert '/.local/state/k270-telephoto-bars-r1/' in row['path']
parts=[]
for offset in range(0,row['jpeg_bytes'],32768):
 code="from pathlib import Path;import hashlib,sys;b=Path("+repr(row['path'])+").read_bytes();assert hashlib.sha256(b).hexdigest()=="+repr(row['sha256'])+";sys.stdout.buffer.write(b["+str(offset)+":"+str(offset+32768)+"])"
 q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);assert len(q.stdout)==min(32768,row['jpeg_bytes']-offset);parts.append(q.stdout)
b=b''.join(parts);assert hashlib.sha256(b).hexdigest()==row['sha256']
p=host.PRIVATE/'tele-bars-private.jpg';assert not p.exists();p.write_bytes(b)
print(json.dumps(dict(copied=True,bytes=len(b),sha256=row['sha256'],pattern_only=True)))
