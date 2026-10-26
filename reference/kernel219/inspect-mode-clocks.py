from pathlib import Path
import json,re

kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
text=(kernel/'drivers/media/i2c/imx471.c').read_text()
legacy={int(a,16):int(b,16) for a,b in re.findall(r'CCI_REG8\(0x(03[0-9a-f]{2})\),\s*0x([0-9a-f]+)',text,re.I)}
modes=json.loads(Path('/mnt/e/edk2-samurai-out/kernel217/factory-imx471-modes-private.json').read_text())['modes']
fields=[0x0301,0x0303,0x0305,0x0306,0x0307,0x030b,0x030d,0x030e,0x030f,0x0310]
print(json.dumps(dict(legacy={hex(a):legacy.get(a) for a in fields},factory=[dict(size=[m['width'],m['height']],registers={hex(a):next((r['value'] for r in m['registers'] if r['address']==a),None) for a in fields}) for m in modes]),indent=2))
