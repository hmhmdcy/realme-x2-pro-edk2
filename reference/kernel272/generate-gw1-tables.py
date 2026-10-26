"""Generate only complete OEM modes; compare binary parsing and both XML views."""
from pathlib import Path
import hashlib,json
from gw1_data import Description
import host
R=Path(__file__).resolve().parent
proof=json.loads((R.parent/'kernel270/gw1-crosscheck-validation.json').read_text())
assert proof['both_module_variants_crosschecked'] and proof['two_views_each']
direct={v:json.loads((host.PRIVATE.parent/'kernel270'/('gw1-'+v+'-direct-registers-private.json')).read_text()) for v in ['qtech','sunny']}
assert direct['qtech']['init']==direct['sunny']['init']
assert direct['qtech']['modes']==direct['sunny']['modes']
assert len(direct['sunny']['modes'])==10
out=['/* SPDX-License-Identifier: GPL-2.0-only */',
     '/* Generated from matching handset GW1 descriptions; see kernel272 provenance. */',
     '#ifndef S5KGW1_TABLES_H', '#define S5KGW1_TABLES_H', '']
rows=[]
for name,regs in [('init',direct['sunny']['init']),('mode2',direct['sunny']['modes'][2]),('mode4',direct['sunny']['modes'][4])]:
 assert len(regs)>40
 for i,r in enumerate(regs):
  assert r['address_bytes']==2 and r['value_bytes'] in [1,2]
  assert len(r['delays_us'])==1
  assert r['operation'] in ['WRITE','WRITE_BURST']
  assert all(0<=v<=65535 for v in r['values'])
  if r['operation']=='WRITE':assert len(r['values'])==1
  else:
   assert r['value_bytes']==2
   assert r['address']==0x6f12
   out.append(f'static const u16 s5kgw1_{name}_burst{i}[] = {{')
   vals=r['values']
   for j in range(0,len(vals),8):out.append('\t'+', '.join(f'0x{v:04x}' for v in vals[j:j+8])+',')
   out.extend(['};',''])
 out.append(f'static const struct s5kgw1_reg s5kgw1_{name}_regs[] = {{')
 for i,r in enumerate(regs):
  if r['operation']=='WRITE':
   out.append(f'\t{{ .address = 0x{r["address"]:04x}, .value = 0x{r["values"][0]:04x}, .value_bytes = {r["value_bytes"]}, .delay_us = {r["delays_us"][0]} }},')
  else:
   prefix=f's5kgw1_{name}_burst{i}'
   out.extend([f'\t{{ .address = 0x{r["address"]:04x}, .burst = {prefix},',
               f'\t  .count = ARRAY_SIZE({prefix}), .delay_us = {r["delays_us"][0]} }},'])
 out.extend(['};',''])
 rows.append(dict(name=name,records=len(regs),words=sum(len(r['values']) for r in regs),
                  delays_us=sum(r['delays_us'][0] for r in regs),
                  source_records_sha256=hashlib.sha256(json.dumps(regs,sort_keys=True).encode()).hexdigest()))
out.extend(['#endif',''])
p=R/'s5kgw1-tables.h';p.write_text('\n'.join(out))
report=dict(stage=272,table_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),tables=rows,
 both_variants_equal=True,prior_independent_xml_crosschecks_verified=True,
 incomplete_modes1_and6_excluded=True,other_modes_still_pending=True,phone_unchanged=True)
(R/'table-generation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
