"""OEM MEMSHARE v1 request observer. Never allocate or return physical memory."""
import collections,json,select,socket,struct,threading,time
CTRL=0xfffffffe
def tlvs(data):
 result={};off=0
 while off<len(data):
  if len(data)-off<3:raise ValueError('Short TLV header')
  tag,n=struct.unpack_from('<BH',data,off);off+=3
  if off+n>len(data) or tag in result:raise ValueError('Truncated or duplicate TLV')
  result[tag]=data[off:off+n];off+=n
 return result
def item(tag,b):return struct.pack('<BH',tag,len(b))+b
def u32(values,tag):
 if tag not in values or len(values[tag])!=4:raise ValueError('Missing or malformed uint32 field')
 return struct.unpack('<I',values[tag])[0]
def response(data):
 if len(data)<7:raise ValueError('Short QMI header')
 kind,txn,msg,n=struct.unpack_from('<BHHH',data)
 if kind!=0 or len(data)!=7+n:raise ValueError('Not an exact QMI request')
 v=tlvs(data[7:]);row=dict(message_id=msg,tlv_lengths={hex(k):len(b) for k,b in v.items()});result,error=1,94;extra=b''
 if msg==0x22:
  row.update(requested_bytes=u32(v,1),client_id=u32(v,2),proc_id=u32(v,3),sequence_id=u32(v,4));result,error=1,2;extra=item(0x10,v[4]);row['response']='no_memory'
  if 0x10 in v:
   if len(v[0x10])!=1:raise ValueError('Invalid contiguous flag')
   row['contiguous']=v[0x10][0]
  if 0x11 in v:row['block_alignment']=u32(v,0x11)
 elif msg==0x24:
  row.update(client_id=u32(v,1),proc_id=u32(v,0x10) if 0x10 in v else None)
  if row['client_id'] in [0,1,2] and row['proc_id'] in [None,0]:
   size={0:0,1:5242880,2:0}[row['client_id']];result,error=0,0;extra=item(0x10,struct.pack('<I',size));row.update(response='configured_initial_size_only',configured_initial_bytes=size)
  else:result,error=1,41;row['response']='invalid_client'
 elif msg==0x23:result,error=1,41;row['response']='invalid_id_no_memory_owned'
 else:row['response']='unsupported'
 body=item(2,struct.pack('<HH',result,error))+extra;row.update(response_result=result,response_error=error)
 return row,struct.pack('<BHHH',2,txn,msg,len(body))+body
class Memshare:
 def __init__(self,output):
  self.output=output;self.sock=None;self.published=False;self.publication_confirmed=False;self.withdrawn=False;self.closed=False;self.error=None;self.records=0;self.bytes=0;self.requests=[];self.responses=0;self.malformed=0;self.stop=threading.Event();self.thread=None;self.began=time.monotonic();self.published_ns=None
  try:self.sock=socket.socket(42,socket.SOCK_DGRAM);self.sock.bind((self.sock.getsockname()[0],0));self.sock.settimeout(0.5);self.local=self.sock.getsockname()
  except BaseException:
   if self.sock:self.sock.close()
   self.closed=True;raise
 def record(self,kind,**fields):
  self.output.write(json.dumps(dict(kind=kind,elapsed_ms=round((time.monotonic()-self.began)*1000),monotonic_ns=time.monotonic_ns(),**fields))+'\n');self.output.flush()
 def ns(self,command,instance):
  node,port=self.local;self.sock.sendto(struct.pack('<IIIII',command,52,instance,node,port),(node,CTRL))
 def prepare(self):
  self.ns(10,0);end=time.monotonic()+1
  while time.monotonic()<end:
   if not select.select([self.sock],[],[],min(0.1,end-time.monotonic()))[0]:continue
   b,peer=self.sock.recvfrom(65536);self.record('namespace_preflight_rx',peer=list(peer),hex=b.hex())
   if peer[1]==CTRL and len(b)==20:
    cmd,service,instance,node,port=struct.unpack('<IIIII',b)
    if cmd==4 and service==52:raise RuntimeError('Existing MEMSHARE service; do not replace')
  self.ns(4,0x101);self.published=True;self.published_ns=time.monotonic_ns();self.record('memshare_published',service=52,version=1,instance=1)
  # Independent namespace readback verifies that registration really exists.
  probe=socket.socket(42,socket.SOCK_DGRAM)
  try:
   probe.bind((probe.getsockname()[0],0));node,port=probe.getsockname();probe.sendto(struct.pack('<IIIII',10,52,0,node,port),(node,CTRL));end=time.monotonic()+1
   while time.monotonic()<end:
    if not select.select([probe],[],[],min(0.1,end-time.monotonic()))[0]:continue
    b,peer=probe.recvfrom(65536)
    if peer[1]==CTRL and len(b)==20:
     cmd,service,instance,node,port=struct.unpack('<IIIII',b)
     if cmd==4 and service==52:
      if (instance,node,port)!=(0x101,*self.local):raise RuntimeError('Conflicting MEMSHARE owner')
      self.publication_confirmed=True
   if not self.publication_confirmed:raise RuntimeError('MEMSHARE namespace readback missing')
  finally:probe.close()
  self.record('memshare_publication_confirmed');self.thread=threading.Thread(target=self.run,name='memshare-observer',daemon=False);self.thread.start()
 def poll(self):
  if not select.select([self.sock],[],[],0.1)[0]:return
  b,anc,flags,peer=self.sock.recvmsg(4096);self.records+=1;self.bytes+=len(b)
  if self.records>4096 or self.bytes>2*1024*1024:raise RuntimeError('MEMSHARE capture limit')
  self.record('rx',peer=list(peer),truncated=bool(flags&socket.MSG_TRUNC),hex=b.hex())
  if peer[1]==CTRL or peer[0]!=0:return
  if flags&socket.MSG_TRUNC:raise ValueError('Truncated MEMSHARE datagram')
  try:row,reply=response(b)
  except ValueError as e:
   self.malformed+=1;self.record('malformed_request',error=str(e))
   if len(b)>=7 and b[0]==0:
    _,txn,msg,_=struct.unpack_from('<BHHH',b);body=item(2,struct.pack('<HH',1,1));self.sock.sendto(struct.pack('<BHHH',2,txn,msg,len(body))+body,peer)
   if self.malformed>16:raise
   return
  if len(self.requests)>=256:raise RuntimeError('Too many MEMSHARE requests')
  row['elapsed_ms']=round((time.monotonic()-self.began)*1000);self.sock.sendto(reply,peer);self.responses+=1;self.requests.append(row);self.record('request_response',request=row)
 def run(self):
  try:
   while not self.stop.is_set():self.poll()
  except BaseException as e:self.error=repr(e)
  finally:self._close_socket()
 def _close_socket(self):
  if self.closed:return
  try:
   if self.published:self.ns(5,0x101);self.withdrawn=True
  finally:
   self.sock.close();self.closed=True;self.record('memshare_cleanup',withdrawal_sent=self.withdrawn,socket_closed=True,error=self.error)
 def check(self):
  if self.error:raise RuntimeError('MEMSHARE observer: '+self.error)
 def close(self):
  self.stop.set()
  if self.thread:
   self.thread.join(timeout=3)
   if self.thread.is_alive():raise RuntimeError('MEMSHARE observer still active')
  else:self._close_socket()
  self.check()
 def snapshot(self):
  requests=list(self.requests)
  return dict(service=52,version=1,instance=1,publication_confirmed=self.publication_confirmed,request_count=len(requests),response_count=self.responses,message_counts=dict(collections.Counter(hex(x['message_id']) for x in requests)),requests=requests,malformed_requests=self.malformed,raw_records=self.records,raw_bytes=self.bytes,physical_allocations=0,physical_addresses_returned=0,scm_ownership_changes=0,withdrawal_sent=self.withdrawn,socket_closed=self.closed,error=self.error)
