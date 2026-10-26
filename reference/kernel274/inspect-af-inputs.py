"""Inspect fixed OEM module actuator sections without any lens or sensor I/O."""
from pathlib import Path
import hashlib,json,struct,sys,xml.etree.ElementTree as ET
import host
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'kernel272'))
from gw1_data import Description
rows=[]
for variant in ['sunny','qtech']:
 d=Description(variant);act=d.uid('actuatorDriver');words=d.words(act)
 refs=[]
 for i,w in enumerate(words):
  if w in d.entries:
   e=d.entries[w];b=d.payload(w)
   refs.append(dict(word_index=i,uid=w,name=e['name'],size=e['size'],hex=b.hex() if len(b)<=256 else None))
 names=[dict(uid=u,name=e['name'],value=d.payload(u).split(b'\0')[0].decode(errors='replace')) for u,e in d.entries.items() if e['name']=='actuatorName']
 rows.append(dict(variant=variant,source_sha256=hashlib.sha256(d.raw).hexdigest(),root_words=list(words),references=refs,names=names))
paths=list(Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api').rglob('*actuator*.xsd'))
ns={'x':'http://www.w3.org/2001/XMLSchema'};schemas={}
for p in paths:
 root=ET.parse(p);types={}
 for typ in root.findall('./x:complexType',ns):
  types[typ.attrib['name']]=[{k:e.attrib[k] for k in ['name','type','minOccurs','maxOccurs'] if k in e.attrib} for e in typ.findall('./x:sequence/x:element',ns)]
 schemas[str(p)]=types
out=dict(stage=274,variants=rows,schemas=schemas,no_phone_or_actuator_operation=True)
(host.PRIVATE/'actuator-input-inspection-private.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
