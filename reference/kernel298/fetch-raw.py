"""Fetch only private current-boot reference frames; never publish pixels."""
from pathlib import Path
import hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent
capture=json.loads((HERE/'raw-capture-validation.json').read_text());assert capture['passed']
rows=[]
for frame in [5,11,17]:
 data=bytearray();size=2048*1224
 for offset in range(0,size,262144):
  end=min(size,offset+262144)
  code=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k298-raw-r1/frame-private-{frame}.raw').read_bytes();assert len(b)=={size};sys.stdout.buffer.write(b[{offset}:{end}])"
  q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);assert len(q.stdout)==end-offset;data.extend(q.stdout)
 p=host.PRIVATE/f'raw-{frame}-private.raw';assert not p.exists();p.write_bytes(data)
 rows.append(dict(frame=frame,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
 print('Fetched private RAW frame '+str(frame),flush=True)
(HERE/'raw-transfer-validation.json').write_text(json.dumps(dict(stage=298,frames=rows,scene_darkness_not_confirmed=True,no_dark_calibration_claimed=True),indent=2)+'\n')
