"""Small, bounded modem-only DIAG/QRTR client; no generic write-command API.

Transport constants/framing: linux-msm/diag, pinned in source receipts.
Query API accepts VERSION, EXT_BUILD_ID and LOG_CONFIG range/get-mask only.
Optional logging changes exactly four GNSS log bits, then sends a zero mask.
No sleep votes, buffering modes, NV or RF settings are sent.
"""
import json,select,socket,struct,time
CTRL=0xfffffffe
GNSS_LOG_CODES=(0x1477,0x1480,0x1756,0x1886)
def gnss_mask_packet(enabled):
 # Fixed equipment-1 diagnostic log mask only, following diag_cntl.c __packed.
 count=0x0a02;mask=bytearray((count+7)//8)
 if enabled:
  for code in GNSS_LOG_CODES:
   item=code&0xfff;assert code>>12==1 and item<count
   mask[item//8]|=1<<(item%8)
 return struct.pack('<IIBBBII',9,11+len(mask),1,3,1,count,len(mask))+mask
def frames(data):
 result=[];offset=0
 while offset<len(data):
  if len(data)-offset<5 or data[offset:offset+2]!=b'\x7e\x01':raise ValueError('Invalid non-HDLC header')
  length=struct.unpack_from('<H',data,offset+2)[0];end=offset+4+length
  if not length or end>=len(data) or data[end]!=0x7e:raise ValueError('Truncated non-HDLC frame')
  result.append(data[offset+4:end]);offset=end+1
 return result
class Diag:
 def __init__(self,output,observed_control=None):
  self.output=output;self.sockets=[];self.published=[];self.remote_cmd=None;self.control_peer=None
  self.feature_mask=None;self.sent_features=False;self.received=[];self.records=0;self.bytes=0;self.decode_errors=0
  self.tx_control=0;self.tx_commands=0;self.began=time.monotonic();self.closed=False;self.observed_control=observed_control
  self.log_mask_active=False;self.log_mask_reset_sent=False;self.deleted_peers=[]
  guards=[]
  try:
   # Do not reuse the previous published AP endpoints during reconnect.
   for i in range(4):
    s=socket.socket(42,socket.SOCK_DGRAM);s.bind((s.getsockname()[0],0));guards.append(s)
   for name in ['control','data','dci','command']:
    s=socket.socket(42,socket.SOCK_DGRAM);s.bind((s.getsockname()[0],0));self.sockets.append(s)
   self.local_node=self.sockets[0].getsockname()[0]
   self.ns(self.sockets[3],10,0)
   for index,instance in enumerate([0,2,4]):
    self.ns(self.sockets[index],4,instance);self.published.append((index,instance))
   self.record('local_endpoints',ports=[s.getsockname()[1] for s in self.sockets])
  except BaseException:self.close();raise
  finally:
   for s in guards:s.close()
 def record(self,kind,**fields):
  self.output.write(json.dumps(dict(kind=kind,elapsed_ms=round((time.monotonic()-self.began)*1000),**fields))+'\n');self.output.flush()
 def ns(self,s,cmd,instance):
  node,port=s.getsockname();s.sendto(struct.pack('<IIIII',cmd,4097,instance,node,port),(node,CTRL))
 def poll(self,timeout):
  ready,_,_=select.select(self.sockets,[],[],timeout)
  for s in ready:
   data,anc,flags,peer=s.recvmsg(65536)
   if flags&socket.MSG_TRUNC:raise ValueError('Datagram truncated')
   self.bytes+=len(data);self.records+=1
   if self.bytes>8*1024*1024 or self.records>8192:raise RuntimeError('Diagnostic capture bound exceeded')
   index=self.sockets.index(s)
   self.record('rx',channel=index,node=peer[0],port=peer[1],hex=data.hex())
   if peer[1]==CTRL:
    if len(data)!=20:continue
    cmd,service,instance,node,port=struct.unpack('<IIIII',data)
    if cmd==4 and service==4097 and instance==1 and node==0 and port:self.remote_cmd=(node,port)
    if cmd==5 and service==4097 and instance==1 and (node,port)==self.remote_cmd:self.remote_cmd=None
    if cmd==6:
     deleted=struct.unpack_from('<II',data,4);self.deleted_peers.append(deleted)
     if deleted==self.control_peer:
      self.record('control_peer_deleted');self.control_peer=None;self.sent_features=False
     if deleted==self.remote_cmd:self.remote_cmd=None
    continue
   if peer[0]!=0:continue
   if index==0:
    offset=0
    while offset+8<=len(data):
     command,length=struct.unpack_from('<II',data,offset);end=offset+8+length
     if end>len(data):raise ValueError('Truncated control record')
     body=data[offset+8:end]
     if command==8 and not self.sent_features:
      if len(body)<5:raise ValueError('Short feature mask')
      n=struct.unpack_from('<I',body)[0]
      if not 1<=n<=8 or len(body)!=4+n:raise ValueError('Invalid feature mask length')
      self.negotiate(peer,int.from_bytes(body[4:],'little'),n,'fresh_modem_feature')
     offset=end
    if offset!=len(data):raise ValueError('Control trailing bytes')
   elif index in [1,3]:
    try:packets=frames(data)
    except ValueError:self.decode_errors+=1;self.record('unknown_frame',channel=index,bytes=len(data));continue
    for p in packets:self.received.append(p)
 def negotiate(self,peer,remote,n,reason):
  assert peer[0]==0 and 1<=n<=8
  mask=remote&0x2051
  # Only transport support bits, deliberately omit master masks and DIAG_ID.
  # Upstream advertises a uint32_t mask even when modem advertises 3 bytes.
  outgoing_width=max(4,n)
  reply=struct.pack('<III',8,4+outgoing_width,outgoing_width)+mask.to_bytes(outgoing_width,'little')
  self.sockets[0].sendto(reply,peer);self.tx_control+=1;self.control_peer=peer;self.feature_mask=mask;self.sent_features=True
  self.record('feature_negotiation',remote_mask=remote,selected_mask=mask,width=n,outgoing_width=outgoing_width,reason=reason)
 def prepare(self):
  end=time.monotonic()+8
  while time.monotonic()<end and not (self.remote_cmd and self.sent_features):
   self.poll(min(0.5,end-time.monotonic()))
  if not self.remote_cmd or not self.sent_features:raise RuntimeError('DIAG handshake incomplete')
 def query(self,payload,seconds=6):
  allowed=payload in [b'\x00',b'\x7c']
  if payload[:4]==b'\x73\0\0\0' and len(payload) in [8,12]:
   op=struct.unpack_from('<I',payload,4)[0];allowed=(op==1 and len(payload)==8) or (op==4 and len(payload)==12)
  if not allowed:raise ValueError('Command outside read-only allowlist')
  if not self.remote_cmd or not self.sent_features:raise RuntimeError('Not prepared')
  self.sockets[3].sendto(payload,self.remote_cmd);self.tx_commands+=1;self.record('query',hex=payload.hex())
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   self.poll(min(0.5,end-time.monotonic()))
   for i,p in enumerate(self.received):
    if p and (p[0]==payload[0] or (p[0] in [0x13,0x14,0x15] and p[1:2]==payload[:1])):
     self.received.pop(i);self.record('response',request_code=payload[0],hex=p.hex());return p
  self.record('query_timeout',request_code=payload[0]);return None
 def gnss_logs(self,enabled):
  if not self.control_peer or not self.sent_features:raise RuntimeError('Transport not ready')
  packet=gnss_mask_packet(enabled);self.sockets[0].sendto(packet,self.control_peer);self.tx_control+=1
  self.log_mask_active=bool(enabled)
  if not enabled:self.log_mask_reset_sent=True
  self.record('gnss_log_mask_sent',enabled=bool(enabled),codes=list(GNSS_LOG_CODES) if enabled else [],equipment=1,previous_mask_not_readable=True)
 def close(self):
  if self.closed:return
  errors=[];removed=0
  if self.log_mask_active:
   try:self.gnss_logs(False)
   except Exception as e:errors.append(getattr(e,'errno',type(e).__name__))
  for i,instance in self.published:
   try:self.ns(self.sockets[i],5,instance);removed+=1
   except OSError as e:errors.append(e.errno)
  for s in self.sockets:
   try:s.close()
   except OSError as e:errors.append(e.errno)
  self.closed=True
  self.record('transport_cleanup',servers_removed=removed,sockets_closed=len(self.sockets),errors=errors,control_messages_sent=self.tx_control,commands_sent=self.tx_commands,log_mask_reset_sent=self.log_mask_reset_sent)
  if errors:raise RuntimeError('Transport cleanup incomplete')

def regression():
 def f(b):return b'\x7e\x01'+struct.pack('<H',len(b))+b+b'\x7e'
 assert frames(f(b'abc')+f(b'def'))==[b'abc',b'def']
 packet=gnss_mask_packet(True);command,size,stream,status,equipment,count,n=struct.unpack_from('<IIBBBII',packet)
 assert (command,size,stream,status,equipment)==(9,len(packet)-8,1,3,1) and n==len(packet)-19
 bits=[0x1000+i for i in range(count) if packet[19+i//8]&(1<<(i%8))]
 assert bits==list(GNSS_LOG_CODES) and not any(gnss_mask_packet(False)[19:])
 for bad in [b'',b'\x7e',b'\x7e\x02\x01\x00x\x7e',b'\x7e\x01\xff\xffx\x7e',f(b'x')[:-1],f(b'x')+b'x']:
  try:result=frames(bad)
  except ValueError:continue
  assert bad==b'' and result==[]
 return dict(multiple_frames=True,malformed_and_truncated_rejected=True,gnss_mask_only_four_verified_ids=True,disable_mask_empty=True)

if __name__=='__main__':print(json.dumps(regression()))
