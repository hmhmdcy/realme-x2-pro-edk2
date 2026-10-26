from pathlib import Path
import collections,json,struct
P=Path('/mnt/e/edk2-samurai-out/kernel298');raw=(P/'sunny-imx319-tuning-private.bin').read_bytes();d=json.loads((P/'imx319-tuning-symbols-private.json').read_text());byid={r['uid']:r for r in d['symbols']}
def words(r):
 b=raw[d['base']+r['offset']:d['base']+r['offset']+r['size']];assert len(b)%8==0
 return struct.unpack('<'+'Q'*(len(b)//8),b)
def f(w):return struct.unpack('<f',struct.pack('<I',w&0xffffffff))[0]
leaves=[r for r in d['symbols'] if r['name']=='mod_bls12_cct_data'];sizes=collections.Counter(r['size'] for r in leaves)
assert set(sizes)=={56}
values=[dict(uid=r['uid'],cct_trigger=[f(v) for v in words(r)[:2]],offset=f(words(r)[2]),thresholds_r_gr_gb_b=[f(v) for v in words(r)[3:]]) for r in leaves]
roots=[]
for r in d['symbols']:
 if r['name'] not in ['bls12_ife','mod_bls12_aec_data','mod_bls12_led_idx_data','mod_bls12_hdr_aec_data','mod_bls12_drc_gain_data']:continue
 if any(z['name']==r['name'] for z in roots):continue
 roots.append(dict(name=r['name'],uid=r['uid'],size=r['size'],words=[dict(index=i,integer=v,float=f(v),referenced_symbol=byid[v]['name'] if v in byid else None) for i,v in enumerate(words(r))]))
report=dict(candidate_only=True,schema_layout_crosscheck_pending=True,ife_vs_bps_reachability_pending=True,leaf_count=len(leaves),leaf_sizes=dict(sizes),offset_value_counts=dict(collections.Counter(v['offset'] for v in values)),threshold_tuple_counts={str(k):v for k,v in collections.Counter(tuple(r['thresholds_r_gr_gb_b']) for r in values).items()},roots=roots,leaves=values)
(P/'bls-candidate-decode-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='leaves'},indent=2))
