"""VERSION only: compare connected raw, non-HDLC and escaped CRC framing."""
from pathlib import Path
import json,os,struct,sys,time,traceback
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
sys.path.insert(0,str(r/'k243-diag-python-r4'));from diag_transport import Diag
o=r/'k243-diag-framing';assert not o.exists();o.mkdir(mode=0o700)
rows=[json.loads(x) for x in (r/'k243-diag-passive-r3/events-private.jsonl').read_text().splitlines()]
f=next(x for x in rows if x.get('channel')=='control' and bytes.fromhex(x['hex'])[:4]==struct.pack('<I',8));b=bytes.fromhex(f['hex']);n=struct.unpack_from('<I',b,8)[0]
crc=0xffff
for byte in b'\0':
 crc^=byte
 for bit in range(8):crc=(crc>>1)^0x8408 if crc&1 else crc>>1
hdlc=b'\0'+struct.pack('<H',crc^0xffff);hdlc=hdlc.replace(b'\x7d',b'\x7d\x5d').replace(b'\x7e',b'\x7d\x5e')+b'\x7e'
d=None;error=None;results={}
with (o/'events-private.jsonl').open('x') as output:
 try:
  d=Diag(output,((f['node'],f['port']),int.from_bytes(b[12:],'little'),n));d.prepare();d.sockets[3].connect(d.remote_cmd)
  for name,wire in [('raw_connected',b'\0'),('non_hdlc_connected',b'\x7e\x01\x01\x00\x00\x7e'),('hdlc_connected',hdlc)]:
   before=len(d.received);d.sockets[3].send(wire);d.tx_commands+=1;d.record('version_encoding',encoding=name,hex=wire.hex());end=time.monotonic()+4
   while time.monotonic()<end:d.poll(min(0.5,end-time.monotonic()))
   added=d.received[before:];results[name]=dict(packets=len(added),version_responses=sum(bool(p) and p[0]==0 for p in added))
 except BaseException:error=traceback.format_exc();(o/'failure-private.txt').write_text(error)
 finally:
  if d:d.close()
report=dict(stage=243,results=results,failure=bool(error),closed=bool(d and d.closed),no_log_masks=True,semantic_command_version_only=True)
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':{'events':[json.loads(x) for x in (o/'events-private.jsonl').read_text().splitlines()],'failure':error}}))
