from pathlib import Path
import hashlib,json,shlex,sys
import host
R=Path(__file__).parent;run=int(sys.argv[1]);proof=json.loads((R/('camera-'+str(run)+'-validation.json')).read_text())['probe_result'];assert proof['image_done_message']
target=host.PRIVATE/('camera-'+str(run)+'-private.jpg');assert not target.exists()
code="from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/var/lib/samurai/k265-user/camera-"+str(run)+"/photo-private.jpg').read_bytes())"
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);assert len(q.stdout)==proof['saved_jpeg_bytes'] and hashlib.sha256(q.stdout).hexdigest()==proof['jpeg_sha256'];target.write_bytes(q.stdout)
print(json.dumps(dict(run=run,private_photo_exported=True,sha256_verified=True,bytes=len(q.stdout))))
