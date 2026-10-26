"""Fresh-only reconnect after a complete, clean DIAG_ID session."""
from pathlib import Path
import json,os,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k244-reconnect';assert not o.exists();o.mkdir(mode=0o700)
sys.path.insert(0,str(r/'k244-nextboot'));from diag_transport_boot import Diag
d=None;error=None;replies=[]
with (o/'events-private.jsonl').open('x') as output:
 try:
  d=Diag(output);end=time.monotonic()+8
  while time.monotonic()<end:d.poll(min(0.5,end-time.monotonic()))
  if d.sent_features and d.remote_cmd:
   for i in range(2):
    p=d.query(b'\0',seconds=3);replies.append(dict(code=p[0] if p else None,bytes=len(p) if p else 0))
 except BaseException:error=traceback.format_exc()
 finally:
  if d:d.close()
report=dict(stage=244,fresh_feature_received=bool(d and d.feature_mask),diag_ids=len(d.diag_ids) if d else 0,version_responses=replies,closed=bool(d and d.closed),failure=bool(error))
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':{'failure':error,'events':[json.loads(x) for x in (o/'events-private.jsonl').read_text().splitlines()]}}))
