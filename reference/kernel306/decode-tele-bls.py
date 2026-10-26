"""Decode every reachable telephoto BLS leaf with bounded typed-vector references."""
from pathlib import Path
import collections,hashlib,json,math,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
raw=(P/'qtech-s5k3m5sx-tuning-private.bin').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='a9059286f6acf1c5d76a1f943e9f62bf3358c019f1e0b419c24b073fec56da1b'
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,so,ss=sections[0];_,base,size=sections[1];assert ss%72==0
symbols=[]
for pos in range(so,so+ss,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode()
 offset,length=struct.unpack_from('<QQ',raw,pos+56);assert offset<=size and length<=size-offset
 symbols.append(dict(uid=uid,name=name,offset=offset,size=length,record_offset=pos))
assert len(set(r['uid'] for r in symbols))==len(symbols)
(P/'tele-tuning-symbols-private.json').write_text(json.dumps(dict(base=base,data_size=size,symbols=symbols),indent=2)+'\n')
byid={r['uid']:r for r in symbols}
def vector(uid,name,n,width):
 assert 0<n<=10000
 r=byid[uid];assert r['name']==name and r['size']==n*width*8
 return [struct.unpack_from('<'+'Q'*width,raw,base+r['offset']+i*width*8) for i in range(n)]
def f(v):
 assert not v>>32
 x=struct.unpack('<f',struct.pack('<I',v))[0];assert math.isfinite(x)
 return x
roots=[]
for root in symbols:
 if root['name'] not in ['bls12_ife','bls12_bps']:continue
 w=vector(root['uid'],root['name'],1,17)[0];assert w[1:4]==(1,2,0) and w[0] in [0,1]
 leaves=[]
 for drc in vector(w[16],'mod_bls12_drc_gain_data',w[15],4):
  for hdr in vector(drc[3],'mod_bls12_hdr_aec_data',drc[2],8):
   for led in vector(hdr[7],'mod_bls12_led_idx_data',hdr[6],3):
    for aec in vector(led[2],'mod_bls12_aec_data',led[1],6):
     for cct in vector(aec[5],'mod_bls12_cct_data',aec[4],7):
      values=[f(v) for v in cct[2:]];assert all(0<=v<=16383 for v in values)
      leaves.append(dict(drc_trigger=[f(v) for v in drc[:2]],hdr_trigger=[f(v) for v in hdr[:6]],led_trigger=led[0],
       aec_trigger=[f(v) for v in aec[:4]],cct_trigger=[f(v) for v in cct[:2]],values=values))
 roots.append(dict(uid=root['uid'],name=root['name'],enabled=w[0],leaves=leaves))
assert roots
(P/'tele-bls-direct-private.json').write_text(json.dumps(dict(roots=roots),indent=2)+'\n')
report=dict(stage=306,source_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=len(raw),
 symbols=len(symbols),ife_roots=sum(r['name']=='bls12_ife' for r in roots),bps_roots=sum(r['name']=='bls12_bps' for r in roots),
 ife_regions=sum(len(r['leaves']) for r in roots if r['name']=='bls12_ife'),
 bps_regions=sum(len(r['leaves']) for r in roots if r['name']=='bls12_bps'),
 unique_values_offset_r_gr_gb_b=sorted(set(tuple(l['values']) for r in roots for l in r['leaves'])),
 source_unchanged=True,typed_vector_bounds_checked=True,independent_factory_parser_pending=True,
 runtime_mode_binding_pending=True,no_calibration_installed=True,no_phone_operation=True)
(HERE/'tele-bls-direct-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
