"""Read metadata for the two selected PDC IDs, never activate a config."""
from pathlib import Path
import json,os,select,socket,struct,time
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();o=r/'k245-pdc-info';assert not o.exists();o.mkdir(mode=0o700)
def tlvs(b):
 v={};i=0
 while i<len(b):
  assert len(b)-i>=3;t,n=struct.unpack_from('<BH',b,i);i+=3;assert i+n<=len(b) and t not in v;v[t]=b[i:i+n];i+=n
 return v
def item(t,b):return struct.pack('<BH',t,len(b))+b
selected={}
for x in json.loads((r/'k245-pdc-read/events-private.json').read_text()):
 b=bytes.fromhex(x['hex'])
 if len(b)>=7:
  kind,txn,msg,n=struct.unpack_from('<BHHH',b)
  if kind==4 and msg==0x22 and n==len(b)-7:
   v=tlvs(b[7:]);assert v[1]==b'\0\0';a=v[0x11];assert len(a)==1+a[0];selected[x['config_type']]=a[1:]
assert set(selected)=={0,1}
s=socket.socket(42,socket.SOCK_DGRAM);s.bind((s.getsockname()[0],0));node,port=s.getsockname();servers=[];records=[];reports={}
try:
 s.sendto(struct.pack('<IIIII',10,36,0,node,port),(node,0xfffffffe));end=time.monotonic()+3
 while time.monotonic()<end:
  if not select.select([s],[],[],min(0.25,end-time.monotonic()))[0]:continue
  b,peer=s.recvfrom(65536)
  if peer[1]==0xfffffffe and len(b)==20:
   cmd,service,instance,remote,p=struct.unpack('<IIIII',b)
   if cmd==4 and service==36 and remote==0:servers.append((instance,remote,p))
 assert len(servers)==1;_,remote,p=servers[0]
 for config_type,label in [(0,'platform'),(1,'software')]:
  txn=1245+config_type;token=245100+config_type;identity=selected[config_type];body=item(1,struct.pack('<IB',config_type,len(identity))+identity)+item(0x10,struct.pack('<I',token));s.sendto(struct.pack('<BHHH',0,txn,0x28,len(body))+body,(remote,p));end=time.monotonic()+10;ack=None;ind=None
  while time.monotonic()<end:
   if not select.select([s],[],[],min(0.25,end-time.monotonic()))[0]:continue
   b,peer=s.recvfrom(65536);records.append(dict(config_type=config_type,peer=list(peer),hex=b.hex()));assert len(records)<=64
   if peer!=(remote,p):continue
   assert len(b)>=7;kind,t,msg,n=struct.unpack_from('<BHHH',b);assert n==len(b)-7;v=tlvs(b[7:])
   if msg!=0x28:continue
   if kind==2 and t==txn:
    assert len(v.get(2,b''))==4;ack=struct.unpack('<HH',v[2])
    if ack[0]!=0:break
   if kind==4 and v.get(0x10)==struct.pack('<I',token):
    assert len(v.get(1,b''))==2;ind=v
   if ack is not None and ind is not None:break
  report=dict(ack_result=ack[0] if ack else None,ack_error=ack[1] if ack else None,indication_received=ind is not None,indication_result=struct.unpack('<H',ind[1])[0] if ind else None)
  if ind:
   for tag,name in [(0x11,'total_bytes'),(0x13,'version')]:
    b=ind.get(tag)
    if b is not None:assert len(b)==4;report[name]=struct.unpack('<I',b)[0]
   b=ind.get(0x12)
   if b is not None:
    assert len(b)>=1 and len(b)==1+b[0];desc=b[1:].decode('ascii');assert 0<len(desc)<=160 and all(32<=ord(c)<127 for c in desc);report['description']=desc
  reports[label]=report
finally:s.close()
(o/'events-private.json').write_text(json.dumps(records,indent=2)+'\n');report=dict(stage=245,service=36,message_allowlist=[40],selected_config_metadata=reports,socket_closed=True,no_config_activation_or_write=True);(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'report':report,'private':dict(events=records)}))
