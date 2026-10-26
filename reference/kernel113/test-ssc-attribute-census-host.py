"""Validate attribute packets and nested values with independent Protobuf."""
from pathlib import Path
import hashlib,importlib.util,json,struct
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
spec=importlib.util.spec_from_file_location('ssc_attributes_tested',ref/'ssc-attribute-census.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
F=descriptor_pb2.FieldDescriptorProto
schema={
 'Uid':[('low',1,F.TYPE_FIXED64,F.LABEL_REQUIRED,None),('high',2,F.TYPE_FIXED64,F.LABEL_REQUIRED,None)],
 'Config':[('processor',1,F.TYPE_INT32,F.LABEL_REQUIRED,None),('suspend_mode',2,F.TYPE_INT32,F.LABEL_REQUIRED,None)],
 'RequestBody':[('msg',2,F.TYPE_BYTES,F.LABEL_OPTIONAL,None)],
 'Request':[('uid',1,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Uid'),('msg_id',2,F.TYPE_FIXED32,F.LABEL_REQUIRED,None),('config',3,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Config'),('request',4,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'RequestBody')],
 'ResponseBody':[('msg_id',1,F.TYPE_FIXED32,F.LABEL_REQUIRED,None),('timestamp',2,F.TYPE_FIXED64,F.LABEL_REQUIRED,None),('msg',3,F.TYPE_BYTES,F.LABEL_REQUIRED,None)],
 'Response':[('uid',1,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Uid'),('response',2,F.TYPE_MESSAGE,F.LABEL_REPEATED,'ResponseBody')],
 'SuidResponse':[('data_type',1,F.TYPE_STRING,F.LABEL_REQUIRED,None),('uid',2,F.TYPE_MESSAGE,F.LABEL_REPEATED,'Uid')],
 'AttrRequest':[('enable_updates',2,F.TYPE_BOOL,F.LABEL_OPTIONAL,None)],
 'Value':[('a',1,F.TYPE_MESSAGE,F.LABEL_OPTIONAL,'Nested'),('s',2,F.TYPE_STRING,F.LABEL_OPTIONAL,None),('f',3,F.TYPE_FLOAT,F.LABEL_OPTIONAL,None),('i',4,F.TYPE_FIXED64,F.LABEL_OPTIONAL,None),('b',5,F.TYPE_BOOL,F.LABEL_OPTIONAL,None)],
 'Nested':[('element',1,F.TYPE_MESSAGE,F.LABEL_REPEATED,'Value')],
 'Array':[('v',1,F.TYPE_MESSAGE,F.LABEL_REPEATED,'Value')],
 'Attr':[('id',1,F.TYPE_INT32,F.LABEL_REQUIRED,None),('value_array',2,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Array')],
 'Attrs':[('attr',1,F.TYPE_MESSAGE,F.LABEL_REPEATED,'Attr')],
}
proto=descriptor_pb2.FileDescriptorProto(name='independent-ssc-attributes.proto',syntax='proto2')
for name,fields in schema.items():
    message=proto.message_type.add(name=name)
    for label,number,kind,repeated,target in fields:
        field=message.field.add(name=label,number=number,type=kind,label=repeated)
        if target:field.type_name='.'+target
pool=descriptor_pool.DescriptorPool();pool.Add(proto);factory=message_factory.MessageFactory(pool)
classes={name:factory.GetPrototype(pool.FindMessageTypeByName(name)) for name in schema}
frame=client.attribute_request(1001,(123,456))
control,txn,mid,size=struct.unpack_from('<BHHH',frame)
assert (control,txn,mid,size)==(0,1001,32,len(frame)-7)
index=7;tlvs={}
while index<len(frame):
    key,count=struct.unpack_from('<BH',frame,index);index+=3
    tlvs[key]=frame[index:index+count];index+=count
payload=tlvs[1];assert struct.unpack_from('<H',payload)[0]==len(payload)-2 and tlvs[16]==b'\x01'
request=classes['Request'].FromString(payload[2:]);assert request.IsInitialized()
assert request.msg_id==1 and (request.uid.low,request.uid.high)==(123,456)
inner=classes['AttrRequest'].FromString(request.request.msg)
assert inner.HasField('enable_updates') and not inner.enable_updates
attrs=classes['Attrs']()
for identifier,text in [(0,'fixture_sensor\x00'),(1,'fixture_vendor\x00'),(2,'accel\x00')]:
    attrs.attr.add(id=identifier).value_array.v.add(s=text)
attrs.attr.add(id=3).value_array.v.add(b=False)
attrs.attr.add(id=21).value_array.v.add(b=True)
value=attrs.attr.add(id=11).value_array.v.add()
value.a.element.add(f=2.5);value.a.element.add(i=42)
decoded=client.attribute_response(attrs.SerializeToString())
assert client.selected_attributes(decoded)==dict(name=['fixture_sensor'],vendor=['fixture_vendor'],data_type=['accel'],available=[False],physical_sensor=[True])
assert decoded[-1]['values']==[{'array':[{'float_bits':struct.unpack('<I',struct.pack('<f',2.5))[0]},{'integer':42}]}]
bad=[b'\x00',b'\x0a\x09',client.wire.bytes_field(1,client.wire.uint(1,3)),
 client.wire.bytes_field(1,client.wire.uint(1,3)+client.wire.bytes_field(2,client.wire.bytes_field(1,client.wire.uint(5,2))))]
rejected=0
for raw in bad:
    try:client.attribute_response(raw)
    except ValueError:rejected+=1
assert rejected==len(bad)
raw=client.wire.bytes_field(2,b'nested')
for _ in range(10):raw=client.wire.bytes_field(1,client.wire.bytes_field(1,raw))
try:client.attribute_value(raw)
except ValueError:rejected+=1
assert rejected==5
report=dict(attribute_message_ids_request1_response128=True,request_decoded_with_independent_google_protobuf=True,
    updates_disabled=True,nested_array_string_float_integer_boolean_fixture_pass=True,
    selected_public_attributes_exclude_matrix_and_calibration=True,malformed_and_depth_cases_rejected=rejected,
    client_sha256=hashlib.sha256((ref/'ssc-attribute-census.py').read_bytes()).hexdigest(),
    phone_runtime_tested=False,phone_changed=False)
(ref/'ssc-attribute-census-host-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
