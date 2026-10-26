from pathlib import Path
import json,struct,xml.etree.ElementTree as E
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel216');private.mkdir(mode=0o700)
binary=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin').read_bytes()
_,data_offset,data_size=struct.unpack_from('<QQQ',binary,0xb8)
entries=json.loads(Path('/mnt/e/edk2-samurai-out/kernel192/imx471-symbol-table-private.json').read_text())
selected=[]
for item in entries:
    if 559<=item['id']<=572:
        data=binary[data_offset+item['offset']:data_offset+item['offset']+item['size']]
        selected.append(dict(**item,words=list(struct.unpack('<'+'Q'*(len(data)//8),data)) if len(data)%8==0 else None,doubles=list(struct.unpack('<'+'d'*(len(data)//8),data)) if len(data)%8==0 else None))
root=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor');schemas={}
for name in ['camxsensordriver.xsd','camxsensorcommon.xsd']:
    lines=(root/name).read_text().splitlines();chosen=set()
    for i,line in enumerate(lines):
        if any(x in line.lower() for x in ['maxanaloggain','minanaloggain','aecd','gains','realto','regtoreal']):chosen.update(range(max(0,i-3),min(len(lines),i+13)))
    schemas[name]={str(i+1):lines[i] for i in sorted(chosen)}
result=dict(entries=selected,schemas=schemas);(private/'own-gain-layout-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
