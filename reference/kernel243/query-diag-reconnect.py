"""One bounded reconnect using fresh endpoints and a uint32 feature reply."""
from pathlib import Path
import json,os,struct,sys,traceback
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
sys.path.insert(0,str(r/'k243-diag-python-r4'));from diag_transport import Diag,regression
o=r/'k243-diag-reconnect-r4';assert not o.exists();o.mkdir(mode=0o700)
rows=[json.loads(x) for x in (r/'k243-diag-passive-r3/events-private.jsonl').read_text().splitlines()]
feature=next(x for x in rows if x.get('channel')=='control' and bytes.fromhex(x['hex'])[:4]==struct.pack('<I',8));b=bytes.fromhex(feature['hex']);n=struct.unpack_from('<I',b,8)[0]
d=None;error=None;response=None
with (o/'events-private.jsonl').open('x') as output:
 try:
  regression();d=Diag(output,((feature['node'],feature['port']),int.from_bytes(b[12:],'little'),n));d.prepare()
  response=d.query(b'\x00')
 except BaseException:error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
 finally:
  if d:d.close()
report=dict(stage=243,failure=bool(error),version_response_bytes=len(response) if response else 0,version_code=response[0] if response else None,closed=bool(d and d.closed),no_log_mask_sent=True)
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':{'response':response.hex() if response else None,'events':[json.loads(x) for x in (o/'events-private.jsonl').read_text().splitlines()],'failure':error}}))
