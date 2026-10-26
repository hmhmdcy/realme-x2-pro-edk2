#!/usr/bin/env python3
"""Discover all SSC UIDs and request attributes; never enable sampling."""
import argparse,collections,hashlib,importlib.util,json,os,socket,struct,sys,time
from pathlib import Path

sys.dont_write_bytecode=True
parent=Path(__file__).resolve().parent
base=parent/'ssc-suid-census.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='7618fe7e4f54b6ce8e9b9437961afc245d7c35b856b0d09e785a391958ad2656'
spec=importlib.util.spec_from_file_location('ssc_wire_base',base)
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
KINDS=['','registry','accel','gyro','mag','ambient_light','proximity','timer','interrupt','resampler']

def attribute_request(transaction,identifier):
    # Published libssc constants: GET_ATTRIBUTES=1, RESPONSE_GET_ATTRIBUTES=128.
    # The optional enable_updates field is 2, as in SscAttrRequest.
    body=(wire.bytes_field(1,wire.uid_bytes(identifier))+wire.fixed32(2,1)+
        wire.bytes_field(3,wire.uint(1,1)+wire.uint(2,0))+
        wire.bytes_field(4,wire.bytes_field(2,wire.uint(2,0))))
    value=struct.pack('<H',len(body))+body
    tlvs=b'\x10\x01\x00\x01'+b'\x01'+struct.pack('<H',len(value))+value
    return struct.pack('<BHHH',0,transaction,32,len(tlvs))+tlvs

def attribute_value(raw,depth=0):
    if depth>8:raise ValueError('attribute nesting exceeds bound')
    fields=wire.protobuf(raw);result={}
    for field,values in fields.items():
        if field not in (1,2,3,4,5):continue
        value=wire.unique(fields,field,bytes if field in (1,2) else int,
            {1:2,2:2,3:5,4:1,5:0}[field])
        if field==1:
            nested=wire.protobuf(value)
            if len(nested.get(1,[]))>256:raise ValueError('attribute array exceeds bound')
            result['array']=[]
            for child in nested.get(1,[]):
                if not isinstance(child,bytes):raise ValueError('invalid nested attribute value')
                result['array'].append(attribute_value(child,depth+1))
        elif field==2:result['string']=value.decode('utf-8')
        elif field==3:
            # Keep exact bits privately, avoiding nonfinite JSON float values.
            result['float_bits']=value
        elif field==4:result['integer']=value
        elif field==5:
            if value not in (0,1):raise ValueError('invalid attribute boolean')
            result['boolean']=bool(value)
    return result

def attribute_response(payload):
    attrs=[];fields=wire.protobuf(payload)
    if len(fields.get(1,[]))>128:raise ValueError('too many attributes')
    for raw in fields.get(1,[]):
        if not isinstance(raw,bytes):raise ValueError('invalid attribute item')
        item=wire.protobuf(raw);identifier=wire.unique(item,1,int,0)
        values=wire.protobuf(wire.unique(item,2,bytes,2))
        if len(values.get(1,[]))>256:raise ValueError('attribute values exceed bound')
        decoded=[]
        for value in values.get(1,[]):
            if not isinstance(value,bytes):raise ValueError('invalid attribute value')
            decoded.append(attribute_value(value))
        attrs.append(dict(id=identifier,values=decoded))
    return attrs

def selected_attributes(attrs):
    result={}
    labels={0:'name',1:'vendor',2:'data_type',3:'available',21:'physical_sensor'}
    for item in attrs:
        if item['id'] not in labels:continue
        values=[]
        for value in item['values']:
            if item['id'] in (0,1,2) and 'string' in value:
                text=value['string'].rstrip('\x00')
                # Only expected identifying attributes are public, never calibration.
                if len(text)<=120 and all(32<=ord(c)<127 for c in text):values.append(text)
            elif item['id'] in (3,21) and 'boolean' in value:values.append(value['boolean'])
        result[labels[item['id']]]=values
    return result

def run(args):
    os.umask(0o077);folder=Path(args.output)
    if folder.exists():raise RuntimeError('output folder must be fresh')
    folder.mkdir(mode=0o700)
    endpoint,listing=wire.locate_service();(folder/'qrtr-services-private.txt').write_text(listing)
    started=time.monotonic();deadline=started+args.duration
    targets={};catalog={};attributes={};operations=[];event_ids=collections.Counter();frames=0;malformed=0
    with (folder/'frames-private.jsonl').open('x') as trace,socket.socket(socket.AF_QIPCRTR,socket.SOCK_DGRAM) as sock:
        sock.bind((sock.getsockname()[0],0));sock.connect(endpoint);sock.settimeout(.5)
        def send(raw,**metadata):
            sock.send(raw);trace.write(json.dumps(dict(direction='tx',elapsed=time.monotonic()-started,hex=raw.hex(),**metadata))+'\n')
        for txn,kind in enumerate(KINDS,1):send(wire.request(txn,kind,False),request_kind='suid',data_type=kind)
        while time.monotonic()<deadline:
            try:raw,ancillary,flags,peer=sock.recvmsg(65536)
            except socket.timeout:continue
            if flags&socket.MSG_TRUNC:raise RuntimeError('truncated QRTR frame')
            frames+=1;record=dict(direction='rx',elapsed=time.monotonic()-started,hex=raw.hex())
            discovered=set()
            try:
                decoded=wire.decode_frame(raw);record['decoded']=decoded
                if 'operation_result' in decoded:
                    operations.append(dict(transaction=decoded['transaction'],result=decoded['operation_result'],error=decoded['operation_error']))
                for event in decoded['events']:
                    event_ids[str(event['message_id'])]+=1
                    if 'suids' in event:
                        values=set(tuple(entry) for entry in event['suids']);discovered.update(values)
                        catalog.setdefault(event['data_type'],set()).update(values)
                    elif event['message_id']==128:
                        identifier=tuple(decoded['sensor_uid'])
                        attrs=attribute_response(bytes.fromhex(event['payload_hex']))
                        event['attributes']=attrs;attributes[identifier]=attrs
            except (ValueError,UnicodeDecodeError,struct.error) as error:
                malformed+=1;record['decode_error']=str(error)
            trace.write(json.dumps(record)+'\n')
            for identifier in sorted(discovered):
                if identifier in targets:continue
                if len(targets)>=64:raise RuntimeError('attribute target bound exceeded')
                txn=1001+len(targets);targets[identifier]=txn
                send(attribute_request(txn,identifier),request_kind='attributes',sensor_uid=identifier)
            trace.flush()
    inventory=[dict(identifier=identifier,attributes=attrs) for identifier,attrs in sorted(attributes.items())]
    (folder/'inventory-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
    (folder/'catalog-private.json').write_text(json.dumps({kind:[list(x) for x in sorted(values)] for kind,values in catalog.items()},indent=2)+'\n')
    public_inventory=[]
    for identifier,txn in sorted(targets.items(),key=lambda x:x[1]):
        attrs=attributes.get(identifier)
        public_inventory.append(dict(ordinal=txn-1000,attribute_response_received=attrs is not None,
            **(selected_attributes(attrs) if attrs is not None else {})))
    ack=collections.Counter(item['transaction'] for item in operations)
    expected=set(range(1,len(KINDS)+1))|set(targets.values())
    complete=bool(targets) and set(attributes)==set(targets) and set(ack)==expected and all(v==1 for v in ack.values())
    failed=sum(item['result']!=0 or item['error']!=0 for item in operations)
    summary=dict(qmi_frames=frames,malformed_frames=malformed,event_ids=dict(event_ids),
        lookup_requests=len(KINDS),attribute_requests=len(targets),attribute_responses=len(attributes),
        all_requests_acknowledged_once=set(ack)==expected and all(v==1 for v in ack.values()),failed_operations=failed,
        duration_seconds=round(time.monotonic()-started,3),inventory=public_inventory,
        suid_types={kind:len(values) for kind,values in catalog.items()},operation_results=operations,
        measurement_stream_requested=False,configuration_changed=False,complete=complete and malformed==0 and failed==0)
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
    return 0 if summary['complete'] else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--duration',type=float,default=25)
    args=parser.parse_args()
    if not 10<=args.duration<=30:parser.error('duration must be 10..30 seconds')
    raise SystemExit(run(args))
