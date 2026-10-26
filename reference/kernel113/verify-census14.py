"""Verify archived phone SUID frames with independent Google Protobuf."""
from pathlib import Path
import collections,hashlib,json,struct,tarfile
from google.protobuf import descriptor_pb2,descriptor_pool,message_factory

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
path=out/'sensor-ram-census14.tar'
with tarfile.open(path) as tar:
    data={}
    for member in tar:
        assert not member.issym() and not member.islnk()
        if not member.isfile():continue
        key=member.name.removeprefix('./')
        assert '..' not in Path(key).parts and not Path(key).is_absolute() and key not in data
        data[key]=tar.extractfile(member).read()
manifest={name.removeprefix('./'):digest for digest,name in
    (line.split('  ',1) for line in data['SHA256SUMS'].decode().splitlines())}
assert set(manifest)==set(data)-{'SHA256SUMS'}
for name,digest in manifest.items():assert hashlib.sha256(data[name]).hexdigest()==digest
with tarfile.open(out/'reboot-audio-clean-14.tar') as tar:
    assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
assert data['trial-exit.txt'].strip()==b'0'
assert data['census-client-check.txt'].strip().endswith(b': OK')
assert data['slpi-final-state.txt'].strip()==b'offline'
assert data['power-final.txt'].strip()==b'vdd=0 vddio=0'
assert data['kernel-state-after.txt'].splitlines()[-1]==b'0'
assert data['firmware-final.txt']==data['firmware-before.txt']
assert data['nv-after.txt'].count(b': OK')==6 and data['source-after.txt'].count(b': OK')==4

# The independent descriptors use the pinned published .proto declarations.
F=descriptor_pb2.FieldDescriptorProto
schema={
 'Uid':[('low',1,F.TYPE_FIXED64,F.LABEL_REQUIRED,None),('high',2,F.TYPE_FIXED64,F.LABEL_REQUIRED,None)],
 'Config':[('processor',1,F.TYPE_INT32,F.LABEL_REQUIRED,None),('suspend_mode',2,F.TYPE_INT32,F.LABEL_REQUIRED,None)],
 'RequestBody':[('msg',2,F.TYPE_BYTES,F.LABEL_OPTIONAL,None)],
 'Request':[('uid',1,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Uid'),('msg_id',2,F.TYPE_FIXED32,F.LABEL_REQUIRED,None),
   ('config',3,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Config'),('request',4,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'RequestBody')],
 'ResponseBody':[('msg_id',1,F.TYPE_FIXED32,F.LABEL_REQUIRED,None),('timestamp',2,F.TYPE_FIXED64,F.LABEL_REQUIRED,None),('msg',3,F.TYPE_BYTES,F.LABEL_REQUIRED,None)],
 'Response':[('uid',1,F.TYPE_MESSAGE,F.LABEL_REQUIRED,'Uid'),('response',2,F.TYPE_MESSAGE,F.LABEL_REPEATED,'ResponseBody')],
 'SuidRequest':[('data_type',1,F.TYPE_STRING,F.LABEL_REQUIRED,None),('enable_updates',2,F.TYPE_BOOL,F.LABEL_OPTIONAL,None),('only_default_values',3,F.TYPE_BOOL,F.LABEL_OPTIONAL,None)],
 'SuidResponse':[('data_type',1,F.TYPE_STRING,F.LABEL_REQUIRED,None),('uid',2,F.TYPE_MESSAGE,F.LABEL_REPEATED,'Uid')],
}
proto=descriptor_pb2.FileDescriptorProto(name='ssc-census14-archive-reference.proto',syntax='proto2')
for name,fields in schema.items():
    message=proto.message_type.add(name=name)
    for label,number,kind,repeated,target in fields:
        field=message.field.add(name=label,number=number,type=kind,label=repeated)
        if target:field.type_name='.'+target
pool=descriptor_pool.DescriptorPool();pool.Add(proto);factory=message_factory.MessageFactory(pool)
classes={name:factory.GetPrototype(pool.FindMessageTypeByName(name)) for name in schema}
lookup=(0xabababababababab,0xabababababababab)
def parse(kind,raw):
    item=classes[kind].FromString(raw);assert item.IsInitialized();return item
def qmi(raw):
    control,txn,msg,size=struct.unpack_from('<BHHH',raw)
    assert size==len(raw)-7
    index=7;tlvs={}
    while index<len(raw):
        key,length=struct.unpack_from('<BH',raw,index);index+=3
        assert key not in tlvs and index+length<=len(raw)
        tlvs[key]=raw[index:index+length];index+=length
    return control,txn,msg,tlvs
def counted(raw):
    assert struct.unpack_from('<H',raw)[0]==len(raw)-2
    return raw[2:]
def uid(item):return (item.low,item.high)

results={};catalogs={}
for mode,default in [('all',False),('default',True)]:
    prefix='census-'+mode+'/'
    exit_code=int(data['census-'+mode+'-exit.txt'])
    if prefix+'summary.json' not in data:
        results[mode]={'exit':exit_code,'completed':False,'independent_frames_verified':False}
        continue
    summary=json.loads(data[prefix+'summary.json'])
    assert summary['only_default_values']==default and summary['enable_updates']
    records=[json.loads(line) for line in data[prefix+'frames-private.jsonl'].decode().splitlines()]
    requested={};operations=[];events=collections.Counter();ever={};latest={};rx_count=0
    malformed=0;independent_indications=0
    for record in records:
        control,txn,msg,tlvs=qmi(bytes.fromhex(record['hex']))
        if record['direction']=='tx':
            assert control==0 and msg==32 and tlvs[16]==b'\x01' and txn not in requested
            request=parse('Request',counted(tlvs[1]))
            assert uid(request.uid)==lookup and request.msg_id==512
            assert request.config.processor==1 and request.config.suspend_mode==0
            inner=parse('SuidRequest',request.request.msg)
            assert inner.only_default_values==default and inner.enable_updates
            assert inner.HasField('only_default_values') and inner.data_type==record['data_type']
            requested[txn]=inner.data_type
            continue
        assert record['direction']=='rx';rx_count+=1
        if 'decode_error' in record:
            malformed+=1;continue
        decoded=record['decoded']
        assert (control,txn,msg)==(decoded['control'],decoded['transaction'],decoded['qmi_message'])
        if control==2 and msg==32:
            result,error=struct.unpack('<HH',tlvs[2])
            assert (result,error)==(decoded['operation_result'],decoded['operation_error'])
            operations.append(dict(transaction=txn,result=result,error=error))
        elif control==4 and msg in (33,34):
            response=parse('Response',counted(tlvs[2]));independent_indications+=1
            assert list(uid(response.uid))==decoded['sensor_uid']
            assert len(response.response)==len(decoded['events'])
            for item,stored in zip(response.response,decoded['events']):
                assert item.msg_id==stored['message_id'] and item.timestamp==stored['timestamp']
                assert item.msg.hex()==stored['payload_hex'];events[str(item.msg_id)]+=1
                if uid(response.uid)==lookup and item.msg_id==768:
                    answer=parse('SuidResponse',item.msg)
                    values=set(uid(entry) for entry in answer.uid)
                    assert answer.data_type==stored['data_type']
                    assert values==set(tuple(entry) for entry in stored['suids'])
                    ever.setdefault(answer.data_type,set()).update(values);latest[answer.data_type]=values
    assert len(requested)==32 and list(requested.values())==summary['requested_types']
    assert rx_count==summary['qmi_frames'] and malformed==summary['malformed_frames']
    assert dict(events)==summary['event_ids'] and operations==summary['operation_results']
    assert {kind:len(values) for kind,values in latest.items()}==summary['suid_types']
    assert {kind:len(values) for kind,values in ever.items()}==summary['suid_types_ever_seen']
    private_catalog=json.loads(data[prefix+'catalog-private.json'])
    assert {kind:set(tuple(x) for x in values) for kind,values in private_catalog.items()}==ever
    transactions=[entry['transaction'] for entry in operations]
    all_acknowledged=set(transactions)==set(requested) and len(transactions)==len(requested)
    failed=sum(entry['result']!=0 or entry['error']!=0 for entry in operations)
    results[mode]=dict(exit=exit_code,completed=True,only_default_values=default,
        requested_types=len(requested),qmi_frames=rx_count,malformed_frames=malformed,
        operation_results=len(operations),all_requests_acknowledged_once=all_acknowledged,
        failed_operations=failed,independent_frames_verified=True,
        independently_decoded_indications=independent_indications,event_ids=dict(events),
        suid_types=summary['suid_types'],duration_seconds=summary['duration_seconds'])
    catalogs[mode]=ever
focus=['accel','gyro','mag','ambient_light','proximity']
counts={kind:{mode:len(catalogs.get(mode,{}).get(kind,set())) for mode in ('all','default')} for kind in focus}
complete=all(item.get('completed') and item['exit']==0 and item['malformed_frames']==0 and
    item['all_requests_acknowledged_once'] and item['failed_operations']==0 for item in results.values())
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nested_files_verified=len(manifest),
    boot_checkpoint='reboot-audio-clean-14',firmware_reference='original-rmx1931-00121',
    modes=results,physical_sensor_suid_counts=counts,full_default_control_complete=complete,
    missing_physical_sensor_suids_not_explained_by_default_filter=(complete and all(counts[k]['all']==counts[k]['default']==0 for k in focus[:-1])),
    original_firmware_selector_restored=True,slpi_offline_and_sensor_power_off=True,
    nv6_sources4_unchanged=True,taint=0,raw_frames_and_suids_private=True,
    sensor_function_accepted=False,goal_complete=False)
(ref/'ssc-census14-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
