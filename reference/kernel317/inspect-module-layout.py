"""Inspect static OEM schema references; never print individual EEPROM values."""
from pathlib import Path
import json,struct,xml.etree.ElementTree as ET
import host
P=host.PRIVATE
source=P.parent/'kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin'
raw=source.read_bytes();table,count=struct.unpack_from('<II',raw,0x98)
sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];base,size=sections[1][1:]
entries={}
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0]
 name=raw[pos+8:pos+40].split(b'\0')[0].decode()
 offset,nbytes=struct.unpack_from('<QQ',raw,pos+56)
 assert offset+nbytes<=size
 entries[uid]=dict(name=name,offset=offset,bytes=nbytes)
rootentry=entries[5];assert rootentry['name']=='EEPROMDriverData'
root=list(struct.unpack_from('<'+'Q'*(rootentry['bytes']//8),raw,base+rootentry['offset']))
record=dict(root_words=root,entries=entries)
(P/'module-layout-private.json').write_text(json.dumps(record,indent=2)+'\n')
schema=P.parent/'kernel117/CamxChi/chi-cdk/api/sensor/camxeepromdriver.xsd'
tree=ET.parse(schema);ns={'x':'http://www.w3.org/2001/XMLSchema'}
mi=tree.find("x:complexType[@name='MemoryInfo']/x:sequence",ns)
report=dict(stage=317,root_words=len(root),memory_info_schema_fields=[e.attrib['name'] for e in mi],
 type_arrays=[dict(uid=uid,**entry,root_references=[i for i,v in enumerate(root) if v==uid]) for uid,entry in entries.items() if entry['name'] in ['lightInfo','customInfo']],
 schema_integrity_fields=[e.attrib['name'] for e in tree.findall('.//x:element',ns) if any(s in e.attrib.get('name','').lower() for s in ['checksum','crc','validflag'])],
 original_module_unchanged=True,no_phone_operations=True)
(Path(__file__).resolve().parent/'module-layout-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
print('Root words with static typed references:')
for i,value in enumerate(root):
 label=entries[value]['name'] if value in entries else ''
 print(i,value,label)
