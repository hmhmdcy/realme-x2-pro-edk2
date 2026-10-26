from pathlib import Path
import json,runpy,struct
from hashlib import sha256

root=Path(__file__).resolve().parent
parse=runpy.run_path(str(root/'parse-driver-log.py'))['parse']
folder=root/'synthetic-logs';folder.mkdir(exist_ok=True)
ticks=134000000000000000
one=bytes.fromhex('90045b203136');two=bytes.fromhex('9003616263')
data=(struct.pack('<QBI',ticks,0,len(one))+one+
      struct.pack('<QBI',ticks+100,3,4)+struct.pack('<I',0xc0000120)+
      struct.pack('<QBI',ticks+200,5,len(two))+two+
      struct.pack('<QBI',ticks+300,8,0))
path=folder/'complete.log';path.write_bytes(data)
result,wire=parse(path)
assert result['complete'] and wire==one+two
assert [r['type'] for r in result['records']]==[0,3,5,8]
path=folder/'partial-header.log';path.write_bytes(data+b'\x01\x02')
result2,wire2=parse(path)
assert not result2['complete'] and result2['issue']['reason']=='partial 13-byte header' and wire2==wire
path=folder/'partial-body.log';path.write_bytes(struct.pack('<QBI',ticks,0,6)+one[:3])
result3,wire3=parse(path)
assert not result3['complete'] and result3['issue']['reason']=='partial body' and wire3==b''
report=dict(synthetic_only=True,no_device_evidence=True,cases=['read/status/out-of-order-read/unknown-zero-length','partial header','partial body'],parser_sha256=sha256((root/'parse-driver-log.py').read_bytes()).hexdigest(),successful_read_bytes=len(wire),all_passed=True)
(root/'parser-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
