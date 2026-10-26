"""Inspect root activation and schema layout without exporting coefficients."""
from pathlib import Path
import json,struct,xml.etree.ElementTree as ET
import host
P=host.PRIVATE
rows=[]
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    index=json.loads((P.parent/'kernel333'/(name+'-index-private.json')).read_text())
    raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
    roots=[]
    for uid,e in index['entries'].items():
        if e['name'] not in ['tmc10_sw','tmc11_sw']:continue
        data=raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
        roots.append(dict(uid=int(uid),name=e['name'],words=struct.unpack('<'+'Q'*(len(data)//8),data)))
    rows.append(dict(variant=name,roots=roots))
    print(name,[(r['uid'],r['name'],r['words'][0]) for r in roots])
(P/'root-layout-private.json').write_text(json.dumps(rows,indent=2)+'\n')
schema=ET.parse(P/'sources/tmc_1_0_0.xsd');ns={'x':'http://www.w3.org/2001/XMLSchema'}
for name in ['tmc10_rgn_dataType','chromatix_tmc10_reserveType']:
    node=next(e for e in schema.findall('x:complexType',ns) if e.attrib.get('name')==name)
    print(name,[(e.attrib['name'],[a.attrib for a in e.findall('.//x:attribute',ns)]) for e in node.findall('x:sequence/x:element',ns)])
