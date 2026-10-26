from pathlib import Path
import hashlib,importlib.util,io,json,struct,time
R=Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('mem247',R/'memshare_observer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def request(msg,items):
 body=b''.join(m.item(t,b) for t,b in items);return struct.pack('<BHHH',0,7,msg,len(body))+body
def iv(v):return struct.pack('<I',v)
a=request(0x22,[(1,iv(2097152)),(2,iv(0)),(3,iv(0)),(4,iv(5)),(0x10,b'\x01'),(0x11,iv(11))]);row,reply=m.response(a);kind,txn,msg,n=struct.unpack_from('<BHHH',reply);v=m.tlvs(reply[7:]);assert row['requested_bytes']==2097152 and row['client_id']==0 and (kind,txn,msg,n)==(2,7,0x22,len(reply)-7) and v[2]==struct.pack('<HH',1,2) and v[0x10]==iv(5) and 0x11 not in v
row,reply=m.response(request(0x24,[(1,iv(0)),(0x10,iv(0))]));v=m.tlvs(reply[7:]);assert v[2]==b'\0'*4 and v[0x10]==iv(0) and 0x11 not in v
row,reply=m.response(request(0x24,[(1,iv(2))]));assert m.tlvs(reply[7:])[2]==struct.pack('<HH',1,41)
row,reply=m.response(request(0x1e,[]));assert m.tlvs(reply[7:])[2]==struct.pack('<HH',1,94)
for bad in [a[:-1],a+b'x',request(0x22,[(1,iv(1))]),request(0x24,[(1,iv(0)),(1,iv(1))]),request(0x24,[(1,b'\0')]),b'\x02'+a[1:]]:
 try:m.response(bad)
 except ValueError:continue
 raise AssertionError('Malformed request accepted')
class FakeSocket:
 def __init__(self):self.sent=[]
 def recvmsg(self,n):return a,[],0,(0,20)
 def sendto(self,b,peer):self.sent.append((b,peer));return len(b)
obj=m.Memshare.__new__(m.Memshare);obj.output=io.StringIO();obj.sock=FakeSocket();obj.began=time.monotonic();obj.records=0;obj.bytes=0;obj.requests=[];obj.responses=0;obj.malformed=0
previous=m.select.select
try:m.select.select=lambda *args:([obj.sock],[],[]);obj.poll()
finally:m.select.select=previous
assert len(obj.requests)==1 and obj.responses==1 and len(obj.sock.sent)==1
events=[json.loads(x) for x in obj.output.getvalue().splitlines()];assert events[-1]['kind']=='request_response' and events[-1]['request']['requested_bytes']==2097152
code=(R/'memshare_observer.py').read_bytes();compile(code,'memshare_observer.py','exec');report=dict(stage=247,alloc_request_2m_decoded_but_refused=True,sequence_preserved=True,no_physical_address_tlv=True,gps_query_size_zero_reply=True,unknown_client_refused=True,unknown_message_not_supported=True,malformed_and_duplicate_tlvs_rejected=True,actual_poll_response_and_event_logging_exercised=True,source_sha256=hashlib.sha256(code).hexdigest())
(R/'memshare-wire-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
