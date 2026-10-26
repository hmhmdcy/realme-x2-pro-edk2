"""Check the light wire codec against independent Google Protobuf fixtures."""
from pathlib import Path
import importlib.util
import json
import struct
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('light', root / 'ssc-light-probe.py')
light = importlib.util.module_from_spec(spec)
spec.loader.exec_module(light)
wire = light.load_wire(root.parent / 'kernel113/ssc-suid-census.py')
F = descriptor_pb2.FieldDescriptorProto
schema = {
    'Uid': [('low', 1, F.TYPE_FIXED64, F.LABEL_REQUIRED, None), ('high', 2, F.TYPE_FIXED64, F.LABEL_REQUIRED, None)],
    'Config': [('processor', 1, F.TYPE_INT32, F.LABEL_REQUIRED, None), ('suspend', 2, F.TYPE_INT32, F.LABEL_REQUIRED, None)],
    'Body': [('msg', 2, F.TYPE_BYTES, F.LABEL_OPTIONAL, None)],
    'Request': [('uid', 1, F.TYPE_MESSAGE, F.LABEL_REQUIRED, 'Uid'), ('msg_id', 2, F.TYPE_FIXED32, F.LABEL_REQUIRED, None),
                ('config', 3, F.TYPE_MESSAGE, F.LABEL_REQUIRED, 'Config'), ('request', 4, F.TYPE_MESSAGE, F.LABEL_REQUIRED, 'Body')],
    'Light': [('intensity', 1, F.TYPE_FLOAT, F.LABEL_REPEATED, None), ('accuracy', 2, F.TYPE_INT32, F.LABEL_REQUIRED, None)],
}
proto = descriptor_pb2.FileDescriptorProto(name='light-independent.proto', syntax='proto2')
for name, fields in schema.items():
    message = proto.message_type.add(name=name)
    for label, number, kind, count, target in fields:
        field = message.field.add(name=label, number=number, type=kind, label=count)
        if target:
            field.type_name = '.' + target
pool = descriptor_pool.DescriptorPool()
pool.Add(proto)


def cls(name):
    desc = pool.FindMessageTypeByName(name)
    if hasattr(message_factory, 'GetMessageClass'):
        return message_factory.GetMessageClass(desc)
    return message_factory.MessageFactory(pool).GetPrototype(desc)


for mid, payload in [(1, wire.uint(2, 0)), (513, b'\x0d' + struct.pack('<f', 5)), (514, b''), (10, b'')]:
    raw = light.sensor_request(wire, 41, (123, 456), mid, payload)
    control, txn, message, tlvs = wire.qmi(raw)
    assert (control, txn, message, tlvs[16]) == (0, 41, 32, b'\x01')
    value = tlvs[1]
    assert struct.unpack_from('<H', value)[0] == len(value) - 2
    request = cls('Request').FromString(value[2:])
    assert request.IsInitialized() and request.msg_id == mid
    assert (request.uid.low, request.uid.high) == (123, 456)
    assert request.config.processor == 1 and request.config.suspend == 0
    assert request.request.msg == payload

sample = cls('Light')(intensity=[12.5, 93], accuracy=3)
assert light.light_sample(wire, sample.SerializeToString()) == {'lux': 12.5, 'values': [12.5, 93.0], 'accuracy': 3}
packed = wire.bytes_field(1, struct.pack('<ff', 12.5, 93)) + wire.uint(2, 3)
assert light.light_sample(wire, packed)['lux'] == 12.5
assert cls('Light').FromString(packed).intensity[0] == 12.5
zero = cls('Light')(intensity=[0], accuracy=0)
assert light.light_sample(wire, zero.SerializeToString())['lux'] == 0
rejected = 0
bad = [b'', b'\x0a\x02\x00\x00\x10\x03', wire.uint(1, 12) + wire.uint(2, 3),
       sample.SerializeToString() + wire.uint(2, 3)]
for value in [float('nan'), float('inf'), -1]:
    bad.append(cls('Light')(intensity=[value], accuracy=3).SerializeToString())
bad.append(cls('Light')(intensity=[1], accuracy=4).SerializeToString())
for payload in bad:
    try:
        light.light_sample(wire, payload)
    except ValueError:
        rejected += 1
assert rejected == len(bad)
report = {'request_modes_independently_decoded': 4, 'packed_and_unpacked_light_passed': True,
          'zero_and_unreliable_preserved': True, 'invalid_inputs_rejected': rejected,
          'phone_runtime_tested': False}
(root / 'light-wire-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
