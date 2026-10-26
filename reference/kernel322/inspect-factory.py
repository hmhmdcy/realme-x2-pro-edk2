"""Associate original-reader selectors with independent binary table roots."""
from pathlib import Path
from collections import Counter
import json,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((P.parent/'kernel317/factory-lsc-decoded-private.json').read_text())
channels=['r','gr','gb','b']
def signature(tables):return Counter(tuple(round(v,5) for c in channels for v in t['gains'][c]) for t in tables)
def values(node):return {c.tag:float(c.text) for c in node} if node is not None else None
records=[]
for xml in d['xml']:
 roots=[r['uid'] for r in d['factory'] if signature(r['golden'])==signature(xml['golden']) and signature(r['core'])==signature(xml['core'])]
 path=Path('/home/cy122/x2pro-linux/parser-k317-lsc-r1/xml')/xml['path'];tree=ET.parse(path)
 triggers={}
 for tag in ['lens_position_trigger','drc_gain_trigger','hdr_aec_trigger','aec_trigger','cct_trigger']:
  rows=[values(n) for n in tree.findall('.//'+tag)];triggers[tag]=[json.loads(t) for t in sorted(set(json.dumps(r,sort_keys=True) for r in rows))]
 leds=sorted(set(int(n.text) for n in tree.findall('.//led_idx_trigger')))
 record=dict(selector=xml['path'],matching_binary_uids=roots,base_tables=len(xml['core']),golden_tables=len(xml['golden']),
  rolloff_enable=int(tree.findtext('enable_section/rolloff_enable')),control_method={c.tag:c.text for c in tree.find('control_method')},
  triggers=triggers,led_indices=leds)
 records.append(record)
assert all(r['matching_binary_uids'] for r in records)
(P/'selector-associations-private.json').write_text(json.dumps(records,indent=2)+'\n')
(HERE/'factory-selector-validation.json').write_text(json.dumps(dict(stage=322,roots=records,all_xml_roots_associated=True,association_scope='gain multiset only; does not distinguish trigger trees',definitive_association='trigger-tree-validation.json',unit_values_not_in_report=True,phone_changed=False),indent=2)+'\n')
print(json.dumps(records,indent=2))
