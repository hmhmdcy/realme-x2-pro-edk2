"""Independent Google Protobuf fixtures, bounds checks and event retention."""
from pathlib import Path
import hashlib,importlib.util,json,random,re,struct,sys
from google.protobuf import __version__ as protobuf_version
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113/libssc-suid-reference-private')
spec=importlib.util.spec_from_file_location('census_under_test',ref/'ssc-suid-census.py')
census=importlib.util.module_from_spec(spec);spec.loader.exec_module(census)
source_report=json.loads((ref/'libssc-suid-source-reference.json').read_text())
for entry in source_report['files']:
    assert hashlib.sha256((out/entry['url'].split('/')[-1]).read_bytes()).hexdigest()==entry['sha256']
# Descriptor declarations are copied from the pinned published .proto schema;
# Google Protobuf produces the wire bytes independently of the census encoder.
F=descriptor_pb2.FieldDescriptorProto
declarations={
 'SscUid':[('low',1,F.TYPE_FIXED64,F.LABEL_REQUIRED,None),('high',2,F.TYPE_FIXED64,F.LABEL_REQUIRED,None)],
 'SscClientConfig':[('processor',1,F.TYPE_INT32,F.LABEL_REQUIRED,None),('suspend_mode',2,F.TYPE_INT32,F.LABEL_REQUIRED,None)],
 'SscClientRequestBody':[('msg',2,F.TYPE_BYTES,F.LABEL_OPTIONAL,None)],
 'SscClientRequest':[('uid',1,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'SscUid'),('msg_id',2,F.TYPE_FIXED32,F.LABEL_REQUIRED,None),
  ('config',3,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'SscClientConfig'),('request',4,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'SscClientRequestBody')],
 'SscClientResponseBody':[('msg_id',1,F.TYPE_FIXED32,F.LABEL_REQUIRED,None),('timestamp',2,F.TYPE_FIXED64,F.LABEL_REQUIRED,None),('msg',3,F.TYPE_BYTES,F.LABEL_REQUIRED,None)],
 'SscClientResponse':[('uid',1,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'SscUid'),('response',2,F.TYPE_MESSAGE,F.LABEL_REPEATED,'SscClientResponseBody')],
 'SscSuidRequest':[('data_type',1,F.TYPE_STRING,F.LABEL_REQUIRED,None),('enable_updates',2,F.TYPE_BOOL,F.LABEL_OPTIONAL,None),('only_default_values',3,F.TYPE_BOOL,F.LABEL_OPTIONAL,None)],
 'SscSuidResponse':[('data_type',1,F.TYPE_STRING,F.LABEL_REQUIRED,None),('uid',2,F.TYPE_MESSAGE,F.LABEL_REPEATED,'SscUid')],
}
proto=descriptor_pb2.FileDescriptorProto(name='ssc-independent-fixture.proto',syntax='proto2')
for name,fields in declarations.items():
    message=proto.message_type.add(name=name)
    for name,number,kind,label,target in fields:
        field=message.field.add(name=name,number=number,type=kind,label=label)
        if target:field.type_name='.'+target
pool=descriptor_pool.DescriptorPool();pool.Add(proto);factory=message_factory.MessageFactory(pool)
classes={name:factory.GetPrototype(pool.FindMessageTypeByName(name)) for name in declarations}
for default in (False,True):
    frame=census.request(37,'accel',default)
    flags,transaction,mid,length=struct.unpack_from('<BHHH',frame)
    assert (flags,transaction,mid,length)==(0,37,32,len(frame)-7)
    # Locate payload using the documented QMI TLV lengths, not census.qmi().
    pos=7;data=None
    while pos<len(frame):
        key=frame[pos];count=struct.unpack_from('<H',frame,pos+1)[0];pos+=3
        value=frame[pos:pos+count];pos+=count
        if key==1:data=value
        if key==16:assert value==b'\x01'
    count=struct.unpack_from('<H',data)[0];assert count==len(data)-2
    request=classes['SscClientRequest'].FromString(data[2:]);assert request.IsInitialized()
    assert request.msg_id==512 and (request.uid.low,request.uid.high)==census.LOOKUP
    assert request.config.processor==1 and request.config.suspend_mode==0
    inner=classes['SscSuidRequest'].FromString(request.request.msg)
    assert inner.IsInitialized() and inner.data_type=='accel' and inner.enable_updates
    assert inner.HasField('only_default_values') and inner.only_default_values==default
answer=classes['SscSuidResponse'](data_type='accel')
answer.uid.add(low=123,high=456);answer.uid.add(low=789,high=987)
response=classes['SscClientResponse']();response.uid.low,response.uid.high=census.LOOKUP
response.response.add(msg_id=768,timestamp=1000,msg=answer.SerializeToString())
response.response.add(msg_id=1022,timestamp=1001,msg=b'calibration-fixture-not-measurement')
response.response.add(msg_id=774,timestamp=1002,msg=b'')
payload=response.SerializeToString()
tlv=b'\x02'+struct.pack('<H',len(payload)+2)+struct.pack('<H',len(payload))+payload
frame=struct.pack('<BHHH',4,0,34,len(tlv))+tlv
decoded=census.decode_frame(frame)
assert [x['message_id'] for x in decoded['events']]==[768,1022,774]
assert decoded['events'][0]['suids']==[(123,456),(789,987)]
assert decoded['events'][2]['payload_hex']==''
rejected=0
for bad in [frame[:-1],b'\x00'*6,frame[:7]+b'\x02\xff\xff'+frame[10:],
    struct.pack('<BHHH',4,0,34,4)+b'\x02\x01\x00\x00']:
    try:census.decode_frame(bad)
    except ValueError:rejected+=1
assert rejected==4
for raw in [b'\x00',b'\x09\x01',b'\x12\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01',b'\x80'*10]:
    try:census.protobuf(raw)
    except ValueError:rejected+=1
assert rejected==8
randomizer=random.Random(11318)
for _ in range(512):
    raw=randomizer.randbytes(randomizer.randrange(128))
    try:census.decode_frame(raw)
    except (ValueError,UnicodeDecodeError,struct.error):pass
(out/'independent-google-protobuf-frame.bin').write_bytes(frame)
report=dict(google_protobuf_version=protobuf_version,published_schema_files_hash_verified=len(source_report['files']),
    request_flags_both_default_modes_validated=True,multiple_suids_preserved=True,
    non_1025_and_empty_payload_events_preserved=True,malformed_known_cases_rejected=rejected,
    bounded_random_frames_without_unexpected_exceptions=512,
    client_sha256=hashlib.sha256((ref/'ssc-suid-census.py').read_bytes()).hexdigest(),
    phone_runtime_tested=False,phone_changed=False)
(ref/'ssc-suid-census-host-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
