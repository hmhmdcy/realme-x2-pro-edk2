from pathlib import Path
import json,struct
from engine_model import prepare
import host
P=host.PRIVATE;blob=(P.parent/'kernel380/640x480-port8-cores1-stripe-private.bin').read_bytes()
m,job,commands,reads=prepare(blob,640,480,observe=True)
plain,pjob,pcommands,_=prepare(blob,640,480,observe=False);assert job==pjob and commands==pcommands
minimal=bytearray(len(blob))
for off in reads:minimal[off]=blob[off] if blob[off]!=0xa5 else 0
q,qjob,qcommands,_=prepare(bytes(minimal),640,480,observe=False);assert qjob==pjob and qcommands==pcommands
(P/'640-active-minimal-private.bin').write_bytes(minimal);(P/'640-active-read-set-private.json').write_text(json.dumps({str(k):sorted(v) for k,v in reads.items()})+'\n')
lines=[]
for start,end in [(0,2268),(2268,2892),(2892,3516)]:
 lines.append('AREA '+str(start))
 for off in range(start,end,2):
  value=struct.unpack_from('<H',minimal,off)[0]
  if value:lines.append(f'{off:5} +{off-start:3} {value:5} {value:#06x}')
(P/'active-fields-private.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(read_bytes=len(reads),bounded_observer_matches_unobserved=True,zeroing_unread_and_sentinel_bytes_preserves_entire_generated_command_buffer=True,nonzero_minimal_bytes=sum(x!=0 for x in minimal))))
