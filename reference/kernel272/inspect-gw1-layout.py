from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
import host
R=Path(__file__).resolve().parent
data=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.qtech_s5kgw1.bin').read_bytes()
t,n=struct.unpack_from('<II',data,0x98);sections=[struct.unpack_from('<QQQ',data,t+i*24) for i in range(n)]
_,so,ss=sections[0];_,base,size=sections[1];entries=[]
for pos in range(so,so+ss,72):
 ident=struct.unpack_from('<Q',data,pos)[0];name=data[pos+8:pos+40].split(b'\0')[0].decode();relative,length=struct.unpack_from('<QQ',data,pos+56)
 entries.append(dict(id=ident,name=name,offset=relative,size=length))
selected=[]
for x in entries:
 if any(k in x['name'].lower() for k in ['sensoroutput','aec','regaddrinfo','streamon','streamoff','grouphold','gain','sensordriverdata']):
  b=data[base+x['offset']:base+x['offset']+x['size']]
  selected.append(dict(**x,words=list(struct.unpack('<'+'Q'*(len(b)//8),b)) if len(b)%8==0 and len(b)<=1000 else None))
xml=ET.parse(next(Path('/home/cy122/x2pro-linux/parser-k270-gw1-qtech-b-r2/xml').rglob('sensorDriverData.xml'))).getroot()
modes=[]
for i,node in enumerate(xml.findall('resolutionInfo/resolutionData')):
 scalar={c.tag:(c.text or '').strip() for c in node if not list(c)}
 modes.append(dict(index=i,scalars=scalar))
schema=ET.parse('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor/camxsensordriver.xsd');ns={'x':'http://www.w3.org/2001/XMLSchema'}
types={}
for name in ['SensorDriverData','SensorOutputInformation','AECInformation','RegisterAddressInformation']:
 node=schema.find("./x:complexType[@name='%s']"%name,ns)
 if node is not None:types[name]=[{k:e.attrib[k] for k in ['name','type','minOccurs','maxOccurs'] if k in e.attrib} for e in node.findall('./x:sequence/x:element',ns)]
d=dict(stage=272,selected=selected,mode_scalars=modes,schema_types=types)
(host.PRIVATE/'gw1-layout-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
