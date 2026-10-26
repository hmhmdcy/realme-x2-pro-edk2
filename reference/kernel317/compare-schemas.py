"""Compare the already identified public schema versions with OEM typed arrays."""
from pathlib import Path
import hashlib,json,urllib.request,xml.etree.ElementTree as ET
import host
P=host.PRIVATE;cache=P/'sources';cache.mkdir(exist_ok=True)
url='https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/36fc163a534963a5b3af52186af5efcc63401ad2/chi-cdk/api/sensor/camxeepromdriver.xsd'
new=cache/'camxeepromdriver-2020.xsd'
if not new.exists():new.write_bytes(urllib.request.urlopen(url,timeout=25).read())
ns={'x':'http://www.w3.org/2001/XMLSchema'}
records=[]
for label,path in [('parser117',P.parent/'kernel117/CamxChi/chi-cdk/api/sensor/camxeepromdriver.xsd'),('public2020',new)]:
 tree=ET.parse(path)
 types={e.attrib['name']:e for e in tree.findall('x:complexType',ns)}
 fields={name:[dict(name=e.attrib['name'],type=e.attrib.get('type'),min=e.attrib.get('minOccurs','1'),max=e.attrib.get('maxOccurs','1')) for e in types[name].findall('x:sequence/x:element',ns)] for name in ['MemoryInfo','AFInfo','EEPROMDataFormatInformation','DualCameraSystemInfo']}
 records.append(dict(label=label,bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),fields=fields))
(Path(__file__).resolve().parent/'schema-comparison.json').write_text(json.dumps(dict(stage=317,sources=records),indent=2)+'\n')
print(json.dumps(records,indent=2))
