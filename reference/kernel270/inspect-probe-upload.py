"""Inspect the interrupted upload before resuming; never start the camera."""
from pathlib import Path
import hashlib,json
import host
q=host.ssh("python3 -c \"from pathlib import Path;import hashlib,json;p=Path('/run/samurai-camera270-probes/telephoto-paired-probe270');print(json.dumps(dict(bytes=p.stat().st_size if p.exists() else None,sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,capture_context_exists=Path('/var/lib/samurai/k270-telephoto-paired-r1').exists())))\"",timeout=15)
(host.PRIVATE/'paired-upload-inspection-private.json').write_bytes(q.stdout);print(q.stdout.decode())
