"""Independent protobuf scalar/vector fixtures including malformed and nonfinite inputs."""
from pathlib import Path
import importlib.util,json,math,struct

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('probe',ref/'ssc-vector-probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
helper=probe.module(ref.parent/'kernel184/ssc-light-probe.py','light_reference')
wire=helper.load_wire(ref.parent/'kernel113/ssc-suid-census.py')
# Fixtures use independently specified protobuf tags: repeated float tag=0x0d,
# packed repeated float tag=0x0a, sensor status varint tag=0x10.
fixtures=[([-1.25,0,9.81],3),([0,0,0],0),([25,-16.5,40],2)]
passed=0
for values,status in fixtures:
    unpacked=b''.join(b'\x0d'+struct.pack('<f',v) for v in values)+b'\x10'+bytes([status])
    packed=b'\x0a\x0c'+struct.pack('<fff',*values)+b'\x10'+bytes([status])
    expected=list(struct.unpack('<fff',struct.pack('<fff',*values)))
    assert probe.vector(wire,unpacked)==(expected,status)
    assert probe.vector(wire,packed)==(expected,status)
    passed+=2
bad=[b'',b'\x0a\x02\x00\x00\x10\x03',b'\x08\x00\x10\x03',
    b'\x0a\x08'+struct.pack('<ff',1,2)+b'\x10\x03',
    b'\x0a\x10'+struct.pack('<ffff',1,2,3,4)+b'\x10\x03',
    b'\x0a\x0c'+struct.pack('<fff',1,2,3)+b'\x10\x04',
    b'\x0a\x0c'+struct.pack('<fff',1,2,3)+b'\x10\x03\x10\x03']
for v in [float('nan'),float('inf'),-float('inf')]:bad.append(b'\x0a\x0c'+struct.pack('<fff',v,2,3)+b'\x10\x03')
rejected=0
for value in bad:
    try:probe.vector(wire,value)
    except ValueError:rejected+=1
assert rejected==len(bad)
request=helper.sensor_request(wire,23,(123,456),513,b'\x0d'+struct.pack('<f',25))
control,transaction,message,tlvs=wire.qmi(request)
assert (control,transaction,message)==(0,23,32)
body=wire.protobuf(tlvs[1][2:])
payload=wire.protobuf(wire.unique(body,4,bytes,2))
rate=wire.protobuf(wire.unique(payload,2,bytes,2))
assert struct.unpack('<f',struct.pack('<I',wire.unique(rate,1,int,5)))[0]==25
report=dict(vector_fixture_encodings_passed=passed,invalid_inputs_rejected=rejected,
    zero_and_unreliable_values_preserved=True,negative_vector_components_allowed=True,
    request_rate_payload_checked=True,phone_hardware_verified=False)
(ref/'vector-wire-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
