"""Reuse only original AP ports; no stale-peer control fallback or mask/mode writes."""
from pathlib import Path
import json,os,socket,struct,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k245-fixed-reconnect';assert not o.exists();o.mkdir(mode=0o700)
old=[json.loads(x) for x in (r/'k244-nextboot/capture/diag-events-private.jsonl').read_text().splitlines()];ports=next(x['ports'] for x in old if x['kind']=='local_endpoints')
assert not Path('/proc',str(json.loads((r/'k244-nextboot/capture/state-private.json').read_text())['pid'])).exists()
sys.path.insert(0,str(r/'k245-tools'));from diag_fixed import Diag
d=None;error=None;responses=[];bind_errno=None
with (o/'events-private.jsonl').open('x') as output:
 try:
  d=Diag(output,fixed_ports=ports);end=time.monotonic()+4
  while time.monotonic()<end:d.poll(min(0.5,end-time.monotonic()))
  if d.remote_cmd:
   # VERSION is safe before a feature exchange; do not send control to old peers.
   for i in range(2):
    before=len(d.received);d.sockets[3].sendto(b'\0',d.remote_cmd);d.tx_commands+=1;d.record('readonly_version_without_stale_control');end=time.monotonic()+3
    while time.monotonic()<end:d.poll(min(0.5,end-time.monotonic()))
    responses.append([dict(code=p[0],bytes=len(p)) for p in d.received[before:] if p])
 except OSError as e:bind_errno=e.errno;error=traceback.format_exc()
 except BaseException:error=traceback.format_exc()
 finally:
  if d:d.close()
report=dict(stage=245,original_ap_ports_reused=True,bind_errno=bind_errno,fresh_feature_received=bool(d and d.feature_mask),diag_ids=len(d.diag_ids) if d else 0,version_responses=responses,closed=bool(d and d.closed),control_messages_sent=d.tx_control if d else 0,mask_or_realtime_mode_not_set=True,failure=bool(error))
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':{'error':error,'events':[json.loads(x) for x in (o/'events-private.jsonl').read_text().splitlines()]}}))
