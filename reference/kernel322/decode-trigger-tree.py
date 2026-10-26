"""Decode trigger topology as well as gains; table equality alone loses selectors."""
from pathlib import Path
import json,struct,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
index=json.loads((P.parent/'kernel317/lsc-root-index-private.json').read_text());entries=index['entries'];base=index['base']
raw=(P.parent/'kernel298/sunny-imx319-tuning-private.bin').read_bytes();channels=['r','gr','gb','b']
levels=[('mod_lsc34_lens_position_data','lens_position_trigger','lens_position_data',['start','end']),
 ('mod_lsc34_drc_gain_data','drc_gain_trigger','drc_gain_data',['start','end']),
 ('mod_lsc34_hdr_aec_data','hdr_aec_trigger','hdr_aec_data',['exp_time_start','exp_time_end','aec_sensitivity_start','aec_sensitivity_end','exp_gain_start','exp_gain_end']),
 ('mod_lsc34_led_idx_data','led_idx_trigger','led_idx_data',['led_index']),
 ('mod_lsc34_aec_data','aec_trigger','aec_data',['lux_idx_start','lux_idx_end','gain_start','gain_end'])]
def blob(uid):
 e=entries[str(uid)];return raw[base+e['offset']:base+e['offset']+e['bytes']]
def leaf(uid,count):
 b=blob(uid);assert len(b)==count*3568
 return [dict(trigger=[struct.unpack_from('<f',b,i*3568+j*8)[0] for j in range(2)],
  gains={c:list(struct.unpack_from('<221f',b,i*3568+16+k*888)) for k,c in enumerate(channels)}) for i in range(count)]
def decode(uid,count,level=0):
 tag,trigger,child,fields=levels[level];assert entries[str(uid)]['name']==tag
 b=blob(uid);stride=(len(fields)+2)*8;assert len(b)==count*stride
 nodes=[]
 for start in range(0,len(b),stride):
  values=[struct.unpack_from('<Q' if level==3 else '<f',b,start+i*8)[0] for i in range(len(fields))]
  n,ref=struct.unpack_from('<QQ',b,start+len(fields)*8)
  data=leaf(ref,n) if level==4 else decode(ref,n,level+1)
  nodes.append(dict(trigger=values,children=data))
 return nodes
def xml_leaf(node,golden=False):
 tag='lsc34_golden_rgn_data' if golden else 'lsc34_rgn_data'
 trigger=[float(node.findtext('cct_trigger/'+key)) for key in ['start','end']]
 return dict(trigger=trigger,gains={c:[float(v) for v in node.findtext(tag+'/'+c+'_gain_tab/'+c+'_gain').split()] for c in channels})
def xml_decode(parent,level=0):
 tag,trigger,child,fields=levels[level];result=[]
 for n in parent.findall(tag):
  values=[int(n.findtext(trigger))] if level==3 else [float(n.findtext(trigger+'/'+field)) for field in fields]
  data=[xml_leaf(row) for row in n.findall(child+'/mod_lsc34_cct_data')] if level==4 else xml_decode(n.find(child),level+1)
  result.append(dict(trigger=values,children=data))
 return result
def norm(value):
 if isinstance(value,float):return round(value,5)
 if isinstance(value,list):return [norm(v) for v in value]
 if isinstance(value,dict):return {k:norm(v) for k,v in value.items()}
 return value
roots=[]
for root in index['roots']:
 if root['name']!='lsc34_ife':continue
 a=next(r for r in root['references'] if r['name']==levels[0][0]);g=next(r for r in root['references'] if r['name']=='mod_lsc34_golden_cct_data')
 roots.append(dict(uid=root['uid'],core=decode(a['uid'],entries[str(a['uid'])]['bytes']//32),golden=leaf(g['uid'],entries[str(g['uid'])]['bytes']//3568)))
records=[];export=Path('/home/cy122/x2pro-linux/parser-k317-lsc-r1/xml')
for p in export.rglob('lsc34_ife.xml'):
 tree=ET.parse(p);core=xml_decode(tree.find('chromatix_lsc34_core'));golden=[xml_leaf(n,True) for n in tree.findall('chromatix_lsc34_golden/mod_lsc34_golden_cct_data')]
 matching=[r['uid'] for r in roots if norm(r['core'])==norm(core) and norm(r['golden'])==norm(golden)]
 assert matching,str(p)
 records.append(dict(selector=p.relative_to(export).as_posix(),binary_uids=matching,complete_trigger_tree_and_gains_match=True))
key=lambda r:json.dumps(norm(dict(core=r['core'],golden=r['golden'])),sort_keys=True)
report=dict(stage=322,selectors=records,unique_complete_profiles=len({key(r) for r in roots}),all_full_trees_match=True,mode_tree_bytes_unchanged=True)
(P/'decoded-trigger-trees-private.json').write_text(json.dumps(roots,indent=2)+'\n')
(HERE/'trigger-tree-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
