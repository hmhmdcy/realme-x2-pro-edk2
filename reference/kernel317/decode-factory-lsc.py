"""Cross-check typed factory LSC arrays and compute private golden/unit factors."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,struct,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
index=json.loads((P/'lsc-root-index-private.json').read_text());entries=index['entries'];base=index['base']
raw=(P.parent/'kernel298/sunny-imx319-tuning-private.bin').read_bytes()
channels=['r','gr','gb','b'];points=221;stride=3568
def data(uid):
 e=entries[str(uid)];return raw[base+e['offset']:base+e['offset']+e['bytes']]
def leaf(uid):
 b=data(uid);assert len(b)%stride==0
 rows=[]
 for start in range(0,len(b),stride):
  trigger=[struct.unpack_from('<f',b,start+i)[0] for i in [0,8]]
  gains={}
  for c,name in enumerate(channels):
   offset=start+16+c*888
   gains[name]=list(struct.unpack_from('<221f',b,offset))
   assert b[offset+884:offset+888]==bytes(4)
   assert all(math.isfinite(v) and v>0 for v in gains[name])
  rows.append(dict(trigger=trigger,gains=gains))
 return rows
def walk(uid,seen):
 if uid in seen:return []
 seen.add(uid);entry=entries[str(uid)]
 if entry['name']=='mod_lsc34_cct_data':return leaf(uid)
 result=[];b=data(uid)
 assert len(b)%8==0
 words=struct.unpack('<'+'Q'*(len(b)//8),b)
 for i,value in enumerate(words):
  child=entries.get(str(value))
  if child and child['name'].startswith('mod_lsc34_'):
   assert i and words[i-1]>0
   result+=walk(value,seen)
 return result
def signature(gains):return tuple(round(value,5) for channel in channels for value in gains[channel])
decoded=[]
for root in index['roots']:
 if root['name']!='lsc34_ife':continue
 core=next(ref for ref in root['references'] if ref['name']=='mod_lsc34_lens_position_data')
 golden=next(ref for ref in root['references'] if ref['name']=='mod_lsc34_golden_cct_data')
 decoded.append(dict(uid=root['uid'],golden=leaf(golden['uid']),core=walk(core['uid'],set())))

export=Path('/home/cy122/x2pro-linux/parser-k317-lsc-r1/xml')
xml_rows=[]
def xml_gains(node):return {name:[float(v) for v in node.findtext(name+'_gain_tab/'+name+'_gain').split()] for name in channels}
for path in export.rglob('lsc34_ife.xml'):
 tree=ET.parse(path)
 xml_rows.append(dict(path=str(path.relative_to(export)),golden=[dict(gains=xml_gains(n)) for n in tree.findall('.//lsc34_golden_rgn_data')],
  core=[dict(gains=xml_gains(n)) for n in tree.findall('.//lsc34_rgn_data')]))
for kind in ['golden','core']:
 binary_values=Counter(signature(row['gains']) for root in decoded for row in root[kind])
 xml_values=Counter(signature(row['gains']) for root in xml_rows for row in root[kind])
 assert binary_values==xml_values,kind+' mismatch between direct typed decoder and original reader'

unit=json.loads((P.parent/'kernel304/unit-wb-lsc-private.json').read_text())
layout=json.loads((P.parent/'kernel304/original-wb-lsc-layout-private.json').read_text())
unit_rows=unit['lsc'];assert len(unit_rows)==5 and all(len(c)==221 for row in unit_rows for c in row['channels'])
# The OEM calibration path uses R,GR,GB,B. The five declared lights can alias
# a single physical EEPROM table; they must not be counted as five readings.
assert all(row['channels']==unit_rows[0]['channels'] for row in unit_rows)
unit_gains=dict(zip(channels,unit_rows[0]['channels']))
zero_samples=sum(value==0 for values in unit_gains.values() for value in values)
factors=[]
for root in decoded:
 assert len(root['golden'])==1
 golden=root['golden'][0]['gains']
 ratios={name:[g/u if u else None for g,u in zip(golden[name],unit_gains[name])] for name in channels}
 calibrated=[{name:[b*f if f is not None else None for b,f in zip(row['gains'][name],ratios[name])] for name in channels} for row in root['core']]
 # The stock path equalizes green gains after multiplying the factors.
 # Keep invalid source nodes explicit instead of inventing replacement data.
 for row in calibrated:
  green=[(gr+gb)/2 if gr is not None and gb is not None else None for gr,gb in zip(row['gr'],row['gb'])]
  row['gr']=green;row['gb']=green.copy()
 assert all(v is None or math.isfinite(v) and v>0 for row in calibrated for values in row.values() for v in values)
 factors.append(dict(uid=root['uid'],golden_over_unit=ratios,full_sensor_calibrated_core=calibrated))
(P/'factory-lsc-decoded-private.json').write_text(json.dumps(dict(factory=decoded,xml=xml_rows,unit_factors=factors,applied=False),indent=2)+'\n')
report=dict(stage=317,factory_ife_roots=len(decoded),golden_regions=sum(len(r['golden']) for r in decoded),
 core_regions=sum(len(r['core']) for r in decoded),mesh_points=221,channel_order=channels,
 direct_decoder_and_original_reader_match=True,float_array_payload_bits=32,float_arrays_padded_to_8_bytes=True,
 declared_eeprom_illuminants=5,unique_physical_lsc_tables=len({tuple(tuple(row) for row in light['channels']) for light in unit_rows}),
 unique_wb_address_maps=len({tuple(row[1:]) for row in layout['wb_lights']}),
 combination='interpolated_base_gain * interpolated(golden_response / unit_response); then GR=GB=mean(GR,GB)',
 unit_zero_samples=zero_samples,unit_candidate_all_nodes_usable=zero_samples==0,
 candidate_geometry_from_titan_source=[17,13],mode_geometry_mapping_verified=False,
 unit_factory_checksum_verified=False,module_vendor_binding_verified=False,
 private_candidate_factors_computed_for_nonzero_nodes=True,invalid_nodes_repaired=False,
 individual_values_applied=False,no_phone_operations=True)
(HERE/'factory-lsc-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
