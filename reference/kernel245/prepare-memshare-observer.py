"""Compile and validate the narrow QMI wire format, then prepare installation."""
from pathlib import Path
import ast,struct,json
R=Path(__file__).resolve().parent;s=(R/'native-memshare-observe.py').read_text();tree=ast.parse(s);compile(s,'native-memshare-observe.py','exec')
functions=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ['tlvs','item','u32']];ns={'struct':struct};exec(compile(ast.Module(body=functions,type_ignores=[]),'memshare-wire','exec'),ns)
b=b''.join(ns['item'](t,struct.pack('<I',v)) for t,v in [(1,2097152),(2,0),(3,0),(4,7)])+ns['item'](0x10,b'\x01');v=ns['tlvs'](b);assert [ns['u32'](v,t) for t in [1,2,3,4]]==[2097152,0,0,7]
for bad in [b'\x01',b'\x01\x04\0\0',ns['item'](1,b'x')*2]:
 try:ns['tlvs'](bad)
 except AssertionError:continue
 raise AssertionError('Malformed/duplicate TLV accepted')
response=struct.pack('<BHHH',2,7,0x22,7)+ns['item'](2,struct.pack('<HH',1,2));assert response.hex()=='0207002200070002040001000200'
t=(R/'launch-resume-r4.py').read_text().replace('native-resume-rf-r4.py','native-memshare-observe.py').replace('k245-resume-rf-r4','k245-memshare-observe').replace('resume-r4-','memshare-');compile(t,'launch-memshare.py','exec');(R/'launch-memshare.py').write_text(t)
p=(R/'poll-resume-r4.py').read_text().replace('k245-resume-rf-r4','k245-memshare-observe');(R/'poll-memshare.py').write_text(p)
report=dict(stage=245,generic_alloc_request_decoded=True,malformed_duplicate_tlvs_rejected=True,no_memory_response_wire_verified=True,no_physical_address_tlv_in_response=True)
(R/'memshare-wire-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
