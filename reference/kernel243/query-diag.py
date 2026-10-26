"""Negotiate transport and request only modem build/version and log-mask metadata."""
from pathlib import Path
import json,os,struct,subprocess,sys,traceback
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
sys.path.insert(0,str(r/'k243-diag-python-r2'));from diag_transport import Diag,regression
o=r/'k243-diag-query-r2';assert not o.exists();o.mkdir(mode=0o700);before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before)
observed=[json.loads(x) for x in (r/'k243-diag-passive-r3/events-private.jsonl').read_text().splitlines()]
feature=next(x for x in observed if x.get('channel')=='control' and bytes.fromhex(x['hex'])[:4]==struct.pack('<I',8))
b=bytes.fromhex(feature['hex']);width=struct.unpack_from('<I',b,8)[0];assert len(b)==12+width
observed_control=((feature['node'],feature['port']),int.from_bytes(b[12:],'little'),width)
responses={};error=None;d=None
with (o/'events-private.jsonl').open('x') as output:
 try:
  regression();d=Diag(output,observed_control);d.prepare()
  for name,payload in [('version',b'\x00'),('build_id',b'\x7c'),('log_ranges',struct.pack('<II',0x73,1)),('log_mask_gnss',struct.pack('<III',0x73,4,1))]:
   response=d.query(payload);responses[name]=response.hex() if response is not None else None
 except BaseException:error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
 finally:
  if d:d.close()
(o/'responses-private.json').write_text(json.dumps(responses,indent=2)+'\n')
after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after)
report=dict(stage=243,transport_prepared=bool(d and d.sent_features and d.remote_cmd),transport_closed=bool(d and d.closed),
 responses={name:dict(present=value is not None,bytes=len(value)//2 if value else 0,code=int(value[:2],16) if value else None) for name,value in responses.items()},
 decode_errors=d.decode_errors if d else None,feature_negotiation_only_no_logging_mask_mode_or_rf_changes=True,no_nv_or_memory_commands=True,
 fault_delta={k:after.count(s)-before.count(s) for k,s in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()),failure=bool(error))
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if error:raise SystemExit(1)
