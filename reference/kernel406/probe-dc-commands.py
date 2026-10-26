"""Locate DC-dependent crop registers in actual target command generation."""
from pathlib import Path
import ctypes,importlib.util,json,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('geometry404',HERE.parent/'kernel404/oracle.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o);scope=dict(o.scope);exec(compile(o.text.replace('64 if off==48','96 if off==48'),'ltm-full-fw','exec'),scope);prepare=scope['prepare']
lib=ctypes.CDLL(str(P.parent/'kernel405/combined-colour.so'));lib.camss_a5_ipe_encode_ltm_iq.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p];lib.camss_a5_ipe_encode_ltm_iq.restype=ctypes.c_int
rows=[]
for width in [640,650]:
 results=[]
 for dc in [0,1]:
  values=[0,0,1,0,19,38,7,0,0,1023,0,0,0,0,0,0,0,0,0,0,dc,1];typed=bytearray(2800);struct.pack_into('<22I12H',typed,0,*values,*([0x101]*12));ltm=ctypes.create_string_buffer(bytes(typed));out=ctypes.create_string_buffer(8944)
  assert not lib.camss_a5_ipe_encode_ltm_iq(out,8944,o.r.f.DATA+0x40000,None,None,ltm)
  iq=out.raw;stripe,_,_=o.striping(width,480,8,2,iq);m,job,cdm=prepare(stripe,width,480,8,2,iq)
  for name,data in [('iq',iq),('stripe',stripe),('job',job),('cdm',cdm)]: (P/f'width-{width}-dc-{dc}-{name}-private.bin').write_bytes(data)
  results.append((stripe,job,cdm))
 a,b=results;diff=[i for i in range(0,len(a[2]),4) if a[2][i:i+4]!=b[2][i:i+4]]
 row=dict(width=width,different_stripe_halfwords=[(i,struct.unpack_from('<H',a[0],i)[0],struct.unpack_from('<H',b[0],i)[0]) for i in range(0,len(a[0]),2) if a[0][i:i+2]!=b[0][i:i+2]],job_equal=a[1]==b[1],different_command_words=[dict(offset=i,before=hex(struct.unpack_from('<I',a[2],i)[0]),after=hex(struct.unpack_from('<I',b[2],i)[0]),preceding=hex(struct.unpack_from('<I',b[2],i-4)[0]) if i>=4 else None) for i in diff]);rows.append(row)
 print(json.dumps(row),flush=True)
(P/'dc-command-differences-private.json').write_text(json.dumps(rows,indent=2)+'\n')
