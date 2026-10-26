"""Locate exact stock WB code and inventory retained factory AWB roots."""
from pathlib import Path
import json, struct
import host
HERE = Path(__file__).resolve().parent
P = host.PRIVATE
s = (HERE.parent / 'kernel320/locate-stock-lsc.py').read_text()
s = s.replace("P=Path('/mnt/e/edk2-samurai-out/kernel320')", "P=Path('/mnt/e/edk2-samurai-out/kernel328')")
s = s.replace("[b'FormatLSCData',b'FormatDataTypeByte',b'meshHWRollOffSize out of bound',b'Memory allocation for LSC failed']",
    "[b'FormatWBData',b'DumpWBData',b'Invalid gbValue in the OTP data',b'illuminantType is TL84 and data is not ok',b'GetTunedMWBData',b'pWBCalibrationData is Null',b'colorTemperature: %d  ratioRG: %f  ratioBG: %f']")
s = s.replace('start=at+1\n  for section', "start=at+1\n  at=raw.rfind(b'\\0',0,at)+1\n  for section")
s = s.replace('stock-lsc-', 'stock-wb-')
exec(compile(s, str(HERE / 'inspect-wb.py'), 'exec'), {'__file__': str(HERE / 'inspect-wb.py')})
inventory = []
for name, stage, filename in [('qtech_s5kgw1',324,'qtech_s5kgw1-tuning-private.bin'),
    ('sunny_s5kgw1',324,'sunny_s5kgw1-tuning-private.bin'),
    ('sunny_imx471',324,'sunny_imx471-tuning-private.bin'),
    ('qtech_s5k3m5sx',306,'qtech-s5k3m5sx-tuning-private.bin')]:
    raw = (P.parent / ('kernel'+str(stage)) / filename).read_bytes()
    table, count = struct.unpack_from('<II', raw, 0x98)
    sections = [struct.unpack_from('<QQQ', raw, table+i*24) for i in range(count)]
    start, length = sections[0][1:]
    entries = []
    for pos in range(start, start+length, 72):
        uid = struct.unpack_from('<Q', raw, pos)[0]
        tag = raw[pos+8:pos+40].split(b'\0')[0].decode()
        version, increment = struct.unpack_from('<II', raw, pos+40)
        offset, size = struct.unpack_from('<QQ', raw, pos+56)
        if any(term in tag.lower() for term in ['awb', 'mwb', 'white', 'golden', 'calibration', 'reference']):
            entries.append(dict(uid=uid, tag=tag, version=version, increment=increment, offset=offset, bytes=size))
    (P / (name+'-awb-entries-private.json')).write_text(json.dumps(entries, indent=2)+'\n')
    inventory.append(dict(module=name, root_tags=sorted({e['tag'] for e in entries if e['version']}),
        matching_entries=len(entries)))
layouts=json.loads((P.parent/'kernel326/descriptor-layouts-private.json').read_text())
print('WB descriptor metadata:', json.dumps({k:v['lights']['wb']['prefix'] for k,v in layouts.items()}))
print('Retained factory AWB inventory:', json.dumps(inventory, indent=2))
