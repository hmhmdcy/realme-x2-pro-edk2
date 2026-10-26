"""Prepare an honest configured-size query probe; allocations still fail."""
from pathlib import Path
import importlib.util,json,struct
R=Path(__file__).resolve().parent
s=(R/'memshare_observer.py').read_text()
old="if row['client_id']==0 and row['proc_id'] in [None,0]:result,error=0,0;extra=item(0x10,struct.pack('<I',0));row['response']='gps_initial_size_zero'"
new="if row['client_id'] in [0,1,2] and row['proc_id'] in [None,0]:\n   size={0:0,1:5242880,2:0}[row['client_id']];result,error=0,0;extra=item(0x10,struct.pack('<I',size));row.update(response='configured_initial_size_only',configured_initial_bytes=size)"
assert s.count(old)==1;s=s.replace(old,new);compile(s,'memshare_configured.py','exec');(R/'memshare_configured.py').write_text(s)
spec=importlib.util.spec_from_file_location('configured',R/'memshare_configured.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def request(msg,fields):
 b=b''.join(m.item(t,struct.pack('<I',v)) for t,v in fields);return struct.pack('<BHHH',0,7,msg,len(b))+b
queries={}
for client,size in [(0,0),(1,5242880),(2,0)]:
 row,reply=m.response(request(0x24,[(1,client),(0x10,0)]));values=m.tlvs(reply[7:]);assert values[2]==struct.pack('<HH',0,0) and values[0x10]==struct.pack('<I',size) and row['configured_initial_bytes']==size;queries[client]=size
row,reply=m.response(request(0x22,[(1,5242880),(2,1),(3,0),(4,9)]));values=m.tlvs(reply[7:]);assert values[2]==struct.pack('<HH',1,2) and values[0x10]==struct.pack('<I',9) and 0x11 not in values
row,reply=m.response(request(0x24,[(1,9),(0x10,0)]));assert m.tlvs(reply[7:])[2]==struct.pack('<HH',1,41)
v=dict(stage=247,candidate_queries_match_locked_oem_board_initial_sizes=queries,allocation_reply_no_memory=True,allocation_sequence_preserved=True,no_address_tlv=True,unknown_client_rejected=True,not_a_complete_memshare_provider=True,not_started_at_validation=True)
(R/'configured-query-wire-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
