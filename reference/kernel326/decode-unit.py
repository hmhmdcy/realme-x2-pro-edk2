"""Decode current unit WB/packed40 LSC using the retained stock HAL grouping."""
from pathlib import Path
import json,math,statistics,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'transfer-validation.json').read_text())['passed']
layouts=json.loads((P/'descriptor-layouts-private.json').read_text());models={'sunny_s5kgw1':'s5kgw1','qtech_s5kgw1':'s5kgw1','sunny_imx471':'imx471','qtech_s5k3m5sx':'s5k3m5'}
decoded={};reports=[]
def roughness(v):
 variance=statistics.pvariance(v)
 if not variance:return None
 pairs=[(v[y*17+x],v[y*17+x+1]) for y in range(13) for x in range(16)]+[(v[y*17+x],v[(y+1)*17+x]) for y in range(12) for x in range(17)]
 return statistics.mean((a-b)**2 for a,b in pairs)/(2*variance)
for name,item in layouts.items():
 model=models[name];raw=(P/'reads-r2'/(model+'-read1-private.bin')).read_bytes();lights=item['lights'];w=lights['wb'];l=lights['lsc']
 assert w['prefix'][:4]==[1,1,0,5] and l['prefix'][:3]==[1,1,5] and l['prefix'][4:]==[221,5,5,5,5]
 def integer(offset,mask):
  assert mask in [0,65535]
  return int.from_bytes(raw[offset:offset+2],'little') if mask else 0
 def byte(offset,mask):
  assert 0<=offset<len(raw) and 0<mask<=255
  shift=(mask&-mask).bit_length()-1;return (raw[offset]&mask)>>shift
 wb=[];lsc=[];legacy=[];anomalies=[]
 for row in w['rows']:
  r,gr,b,gb=[integer(row[i],row[i+1]) for i in [1,3,5,7]]
  wb.append(dict(illuminant=row[0],channels=[r,gr,gb,b],denominators_positive=gr>0 and gb>0,ratios=[r/gb,b/gb,gr/gb] if gb else None))
 for row in l['rows']:
  channels=[];contiguous=[]
  for c in range(4):
   msb,msbmask,lsb,lsbmask=row[1+c*4:5+c*4]
   assert msb==row[3]+4 and msbmask==[192,48,12,3][c] and lsbmask==255
   if lsb!=row[3]+c:anomalies.append(dict(illuminant=row[0],channel=['R','GR','GB','B'][c],declared_low_byte_address=lsb,regular_packed40_low_byte_address=row[3]+c))
   values=[(byte(msb+5*i+i//51,msbmask)<<8)|byte(lsb+5*i+i//51,lsbmask) for i in range(221)]
   old=[(byte(msb+5*i,msbmask)<<8)|byte(lsb+5*i,lsbmask) for i in range(221)]
   channels.append(values);contiguous.append(old)
  lsc.append(dict(illuminant=row[0],channels=channels));legacy.append(contiguous)
 unique_maps=len({tuple(row[1:]) for row in l['rows']})
 unique_tables=len({tuple(tuple(ch) for ch in row['channels']) for row in lsc})
 zero=sum(v==0 for ch in lsc[0]['channels'] for v in ch);oldzero=sum(v==0 for ch in legacy[0] for v in ch)
 base=l['rows'][0][3];footers=[raw[base+group*256+255] for group in range(4)]
 decoded[name]=dict(model=model,eeprom_name=item['eeprom_name'],wb=wb,lsc=lsc,skipped_bytes=footers,descriptor_anomalies=anomalies,neighbor_roughness=[roughness(v) for v in lsc[0]['channels']],applied=False)
 reports.append(dict(module=name,model=model,declared_lights=5,distinct_descriptor_maps=unique_maps,distinct_decoded_lsc_tables=unique_tables,mesh=[17,13],channel_order=['R','GR','GB','B'],samples_per_table=884,
  zero_samples=zero,legacy_contiguous_zero_samples=oldzero,wb_denominators_positive=all(v['denominators_positive'] for v in wb),
  source_start_address=base,extra_byte_after_points=51,skipped_bytes_all_ff=all(v==255 for v in footers),descriptor_anomalies=anomalies,descriptor_anomalies_not_repaired=True,factory_checksum_verified=False))
# The two main descriptors have identical physical WB/LSC maps, despite different names.
assert decoded['sunny_s5kgw1']['lsc']==decoded['qtech_s5kgw1']['lsc'] and decoded['sunny_s5kgw1']['wb']==decoded['qtech_s5kgw1']['wb']
(P/'decoded-unit-private.json').write_text(json.dumps(decoded,indent=2)+'\n')
report=dict(stage=326,modules=reports,stock_hal_grouping_evidence='../kernel320/stock-lsc-layout-validation.json',main_descriptors_share_physical_map=True,
 individual_values_applied=False,normal_light_optical_calibration=False,private_values_not_repaired=True,
 passed=all(r['zero_samples']==0 and r['wb_denominators_positive'] for r in reports))
(HERE/'unit-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
