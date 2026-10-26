from pathlib import Path
import json,struct
out=Path('/mnt/e/edk2-samurai-out/kernel213')
b=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin').read_bytes()
section,count=struct.unpack_from('<II',b,0x98);assert count==3
sections=[struct.unpack_from('<QQQ',b,section+i*24) for i in range(count)]
_,symbol_offset,symbol_size=sections[0];_,data_offset,data_size=sections[1]
entries=json.loads(Path('/mnt/e/edk2-samurai-out/kernel192/imx471-symbol-table-private.json').read_text())
def words(e):
    payload=b[data_offset+e['offset']:data_offset+e['offset']+e['size']]
    assert len(payload)%8==0
    return struct.unpack('<'+'Q'*(len(payload)//8),payload)
selected=[e for e in entries if e['name']=='testPatternData'];assert len(selected)==1
e=selected[0];assert e['size']==48
nearby=[x for x in entries if e['id']<=x['id']<=e['id']+8]
result=[dict(id=x['id'],name=x['name'],words=words(x)) for x in nearby]
(out/'stock-test-pattern-layout-private.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
