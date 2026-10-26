"""Validate captured SSC attributes against independent published descriptors."""
from pathlib import Path
import collections,hashlib,json,runpy,struct,tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
# Reuse independently generated descriptors and tested recursive fixture values.
fixtures=runpy.run_path(str(ref/'test-ssc-attribute-census-host.py'))
classes=fixtures['classes'];client=fixtures['client']
path=out/'sensor-ram-attributes15.tar'
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
with tarfile.open(out/'reboot-audio-clean-15.tar') as tar:
    assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
assert data['trial-exit.txt'].strip()==b'0'
assert data['attribute-client-check.txt'].strip().endswith(b': OK')
assert data['slpi-final-state.txt'].strip()==b'offline' and data['power-final.txt'].strip()==b'vdd=0 vddio=0'
assert data['kernel-state-after.txt'].splitlines()[-1]==b'0'
assert data['nv-after.txt'].count(b': OK')==6 and data['source-after.txt'].count(b': OK')==4
assert data['firmware-final.txt']==data['firmware-before.txt']
prefix='attributes/'
summary=json.loads(data[prefix+'summary.json'])
def parse(kind,raw):
    value=classes[kind].FromString(raw);assert value.IsInitialized();return value
def qmi(raw):
    control,txn,msg,size=struct.unpack_from('<BHHH',raw);assert size==len(raw)-7
    index=7;tlvs={}
    while index<len(raw):
        key,size=struct.unpack_from('<BH',raw,index);index+=3
        assert key not in tlvs and index+size<=len(raw)
        tlvs[key]=raw[index:index+size];index+=size
    return control,txn,msg,tlvs
def counted(raw):
    assert struct.unpack_from('<H',raw)[0]==len(raw)-2;return raw[2:]
def identifier(uid):return (uid.low,uid.high)
def value(item):
    result={}
    if item.HasField('a'):result['array']=[value(x) for x in item.a.element]
    if item.HasField('s'):result['string']=item.s
    if item.HasField('f'):result['float_bits']=struct.unpack('<I',struct.pack('<f',item.f))[0]
    if item.HasField('i'):result['integer']=item.i
    if item.HasField('b'):result['boolean']=item.b
    return result

records=[json.loads(line) for line in data[prefix+'frames-private.jsonl'].decode().splitlines()]
requests={};targets={};catalog={};attrs={};operations=[];events=collections.Counter();rx=0;malformed=0
for record in records:
    control,txn,msg,tlvs=qmi(bytes.fromhex(record['hex']))
    if record['direction']=='tx':
        assert control==0 and msg==32 and txn not in requests and tlvs[16]==b'\x01'
        request=parse('Request',counted(tlvs[1]))
        assert request.config.processor==1 and request.config.suspend_mode==0
        if record['request_kind']=='suid':
            assert request.msg_id==512 and identifier(request.uid)==client.wire.LOOKUP
            decoded=client.wire.protobuf(request.request.msg)
            assert client.wire.unique(decoded,3,int,0)==0 and client.wire.unique(decoded,2,int,0)==1
        else:
            assert record['request_kind']=='attributes' and request.msg_id==1
            inner=parse('AttrRequest',request.request.msg)
            assert inner.HasField('enable_updates') and not inner.enable_updates
            key=identifier(request.uid);assert list(key)==record['sensor_uid'] and key not in targets
            targets[key]=txn
        requests[txn]=record['request_kind'];continue
    assert record['direction']=='rx';rx+=1
    if 'decode_error' in record:malformed+=1;continue
    stored=record['decoded']
    if control==2 and msg==32:
        result,error=struct.unpack('<HH',tlvs[2]);assert (result,error)==(stored['operation_result'],stored['operation_error'])
        operations.append(dict(transaction=txn,result=result,error=error))
    elif control==4 and msg in (33,34):
        response=parse('Response',counted(tlvs[2]));key=identifier(response.uid)
        assert list(key)==stored['sensor_uid'] and len(response.response)==len(stored['events'])
        for item,event in zip(response.response,stored['events']):
            assert item.msg_id==event['message_id'] and item.timestamp==event['timestamp'] and item.msg.hex()==event['payload_hex']
            events[str(item.msg_id)]+=1
            if key==client.wire.LOOKUP and item.msg_id==768:
                answer=parse('SuidResponse',item.msg)
                values=set(identifier(x) for x in answer.uid)
                assert answer.data_type==event['data_type'] and values==set(tuple(x) for x in event['suids'])
                catalog.setdefault(answer.data_type,set()).update(values)
            elif item.msg_id==128:
                answer=parse('Attrs',item.msg)
                decoded=[dict(id=x.id,values=[value(y) for y in x.value_array.v]) for x in answer.attr]
                assert decoded==event['attributes'];attrs[key]=decoded
assert rx==summary['qmi_frames'] and malformed==summary['malformed_frames']
assert dict(events)==summary['event_ids'] and operations==summary['operation_results']
assert len(targets)==summary['attribute_requests'] and len(attrs)==summary['attribute_responses']
assert set(targets)==set(x for values in catalog.values() for x in values)
inventory=[dict(ordinal=txn-1000,attribute_response_received=key in attrs,
    **client.selected_attributes(attrs[key])) for key,txn in sorted(targets.items(),key=lambda x:x[1]) if key in attrs]
assert inventory==[x for x in summary['inventory'] if x['attribute_response_received']]
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nested_files_verified=len(manifest),
    boot_checkpoint='reboot-audio-clean-15',firmware_reference='original-rmx1931-00121',
    client_exit=int(data['attributes-exit.txt']),attribute_control_complete=summary['complete'],
    independently_decoded_qmi_frames=rx,independent_google_protobuf_matches_all_decoded_events=True,
    malformed_frames=malformed,lookup_requests=summary['lookup_requests'],attribute_requests=len(targets),
    attribute_responses=len(attrs),event_ids=dict(events),inventory=summary['inventory'],
    suid_types=summary['suid_types'],all_requests_acknowledged_once=summary['all_requests_acknowledged_once'],
    failed_operations=summary['failed_operations'],original_firmware_selector_restored=True,
    slpi_offline_and_sensor_power_off=True,nv6_sources4_unchanged=True,taint=0,
    raw_frames_uids_attributes_private=True,calibration_changed=False,sensor_function_accepted=False,goal_complete=False)
(ref/'ssc-attributes15-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
