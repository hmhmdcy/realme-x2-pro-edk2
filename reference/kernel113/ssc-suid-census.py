#!/usr/bin/env python3
"""Bounded SSC discovery using the published libssc/SSC wire schema.

Queries the SUID lookup only. It never starts a measurement stream, changes
registry/configuration, or writes outside the caller-provided private folder.
All received QMI frames/events are retained, including unknown event IDs.
"""
import argparse,collections,json,os,socket,struct,subprocess,time
from pathlib import Path

LOOKUP=(0xabababababababab,0xabababababababab)
KINDS=['','registry','accel','gyro','mag','ambient_light','proximity','rotv',
    'gravity','linear_accel','game_rv','geomag_rv','mag_cal','resampler',
    'timer','interrupt','amd','rmd','smd','tilt','device_orient','step_detect',
    'step_count','motion_detect','hall','pressure','humidity','sars','sar',
    'sensor_temperature','accel_cal','gyro_cal']

def varint(n):
    if not 0<=n<2**64: raise ValueError('invalid unsigned varint')
    result=bytearray()
    while n>=128: result.append((n&127)|128);n>>=7
    result.append(n);return bytes(result)

def uint(field,n): return varint(field<<3)+varint(n)
def bytes_field(field,payload): return varint((field<<3)|2)+varint(len(payload))+payload
def fixed32(field,n): return varint((field<<3)|5)+struct.pack('<I',n)
def uid_bytes(uid): return b'\x09'+struct.pack('<Q',uid[0])+b'\x11'+struct.pack('<Q',uid[1])

def read_varint(raw,index):
    value=0
    for shift in range(0,70,7):
        if index>=len(raw):raise ValueError('truncated varint')
        byte=raw[index];index+=1
        if shift==63 and byte>1:raise ValueError('overflowed varint')
        value|=(byte&127)<<shift
        if not byte&128:return value,index
    raise ValueError('unterminated varint')

class Fields(dict):
    def __init__(self):super().__init__();self.wires={}

def protobuf(raw):
    if len(raw)>65535:raise ValueError('oversized protobuf')
    result=Fields();index=0;count=0
    while index<len(raw):
        key,index=read_varint(raw,index);field,wire=key>>3,key&7
        if not 0<field<2**29:raise ValueError('invalid field number')
        if wire==0:value,index=read_varint(raw,index)
        elif wire in (1,5):
            size=8 if wire==1 else 4
            if index+size>len(raw):raise ValueError('truncated fixed field')
            value=int.from_bytes(raw[index:index+size],'little');index+=size
        elif wire==2:
            size,index=read_varint(raw,index)
            if size>len(raw)-index:raise ValueError('truncated length field')
            value=raw[index:index+size];index+=size
        else:raise ValueError('unsupported wire type')
        result.setdefault(field,[]).append(value);result.wires.setdefault(field,[]).append(wire);count+=1
        if count>4096:raise ValueError('excessive protobuf fields')
    return result

def unique(fields,key,kind,wire=None):
    values=fields.get(key,[])
    if len(values)!=1 or not isinstance(values[0],kind):raise ValueError('missing/duplicate/invalid required field')
    if wire is not None and fields.wires.get(key)!=[wire]:raise ValueError('wrong required field wire type')
    return values[0]

def uid(fields):return (unique(fields,1,int,1),unique(fields,2,int,1))

def request(transaction,data_type,default=False,updates=True):
    lookup=bytes_field(1,data_type.encode())+uint(2,int(updates))+uint(3,int(default))
    body=(bytes_field(1,uid_bytes(LOOKUP))+fixed32(2,512)+
        bytes_field(3,uint(1,1)+uint(2,0))+bytes_field(4,bytes_field(2,lookup)))
    value=struct.pack('<H',len(body))+body
    tlvs=b'\x10\x01\x00\x01'+b'\x01'+struct.pack('<H',len(value))+value
    return struct.pack('<BHHH',0,transaction,0x20,len(tlvs))+tlvs

def qmi(raw):
    if len(raw)<7:raise ValueError('short QMI header')
    control,transaction,message,length=struct.unpack_from('<BHHH',raw)
    if length!=len(raw)-7:raise ValueError('QMI size mismatch')
    fields={};index=7
    while index<len(raw):
        if index+3>len(raw):raise ValueError('short QMI TLV header')
        key=raw[index];size=struct.unpack_from('<H',raw,index+1)[0];index+=3
        if index+size>len(raw) or key in fields:raise ValueError('invalid/duplicate QMI TLV')
        fields[key]=raw[index:index+size];index+=size
    return control,transaction,message,fields

def decode_frame(raw):
    control,transaction,message,fields=qmi(raw)
    result=dict(control=control,transaction=transaction,qmi_message=message,events=[])
    if control==2 and message==0x20:
        operation=fields.get(2,b'')
        if len(operation)!=4:raise ValueError('invalid QMI result')
        result['operation_result'],result['operation_error']=struct.unpack('<HH',operation)
    elif control==4 and message in (0x21,0x22):
        data=fields.get(2,b'')
        if len(data)<2:raise ValueError('missing counted indication')
        count=struct.unpack_from('<H',data)[0]
        if count!=len(data)-2:raise ValueError('indication count mismatch')
        decoded=protobuf(data[2:]);sensor_uid=uid(protobuf(unique(decoded,1,bytes)))
        result['sensor_uid']=sensor_uid
        for body in decoded.get(2,[]):
            if not isinstance(body,bytes):raise ValueError('invalid event body')
            event=protobuf(body);mid=unique(event,1,int,5);timestamp=unique(event,2,int,1)
            payload=unique(event,3,bytes)
            item=dict(message_id=mid,timestamp=timestamp,payload_hex=payload.hex())
            if sensor_uid==LOOKUP and mid==768:
                answer=protobuf(payload);kind=unique(answer,1,bytes).decode('utf-8')
                identifiers=[]
                for entry in answer.get(2,[]):
                    if not isinstance(entry,bytes):raise ValueError('invalid SUID entry')
                    identifiers.append(uid(protobuf(entry)))
                item.update(data_type=kind,suids=identifiers)
            result['events'].append(item)
    return result

def locate_service():
    listing=subprocess.run(['qrtr-lookup'],capture_output=True,text=True,timeout=15,check=True).stdout
    candidates=[]
    for line in listing.splitlines():
        fields=line.split()
        if len(fields)>=5 and fields[0]=='400':candidates.append((int(fields[3]),int(fields[4])))
    if len(set(candidates))!=1:raise RuntimeError('SSC service must have one unique endpoint')
    return candidates[0],listing

def run(args):
    os.umask(0o077)
    folder=Path(args.output)
    if folder.exists():raise RuntimeError('output folder must be fresh')
    folder.mkdir(mode=0o700)
    endpoint,listing=locate_service();(folder/'qrtr-services-private.txt').write_text(listing)
    started=time.monotonic();deadline=started+args.duration
    summary=dict(requested_types=KINDS,only_default_values=args.default,enable_updates=True,
        qmi_frames=0,malformed_frames=0,operation_results=[],event_ids={},suid_types={},
        duration_seconds=0,measurement_stream_requested=False,configuration_changed=False)
    events=collections.Counter();catalog={};latest={}
    with (folder/'frames-private.jsonl').open('x') as trace, socket.socket(socket.AF_QIPCRTR,socket.SOCK_DGRAM) as sock:
        sock.bind((sock.getsockname()[0],0));sock.connect(endpoint);sock.settimeout(0.5)
        for transaction,kind in enumerate(KINDS,1):
            raw=request(transaction,kind,args.default)
            sock.send(raw)
            trace.write(json.dumps(dict(direction='tx',elapsed=time.monotonic()-started,data_type=kind,hex=raw.hex()))+'\n')
        while time.monotonic()<deadline:
            try:
                raw,ancillary,flags,peer=sock.recvmsg(65536)
            except socket.timeout:continue
            if flags&socket.MSG_TRUNC:raise RuntimeError('truncated QRTR frame')
            summary['qmi_frames']+=1
            record=dict(direction='rx',elapsed=time.monotonic()-started,hex=raw.hex())
            try:
                decoded=decode_frame(raw);record['decoded']=decoded
                if 'operation_result' in decoded:
                    summary['operation_results'].append(dict(transaction=decoded['transaction'],
                        result=decoded['operation_result'],error=decoded['operation_error']))
                for event in decoded['events']:
                    events[str(event['message_id'])]+=1
                    if 'suids' in event:
                        kind=event['data_type'];values=set(tuple(x) for x in event['suids'])
                        catalog.setdefault(kind,set()).update(values);latest[kind]=values
            except (ValueError,UnicodeDecodeError,struct.error) as error:
                summary['malformed_frames']+=1;record['decode_error']=str(error)
            trace.write(json.dumps(record)+'\n');trace.flush()
    summary['duration_seconds']=round(time.monotonic()-started,3)
    summary['event_ids']=dict(events)
    summary['suid_types']={kind:len(values) for kind,values in sorted(latest.items())}
    summary['suid_types_ever_seen']={kind:len(values) for kind,values in sorted(catalog.items())}
    summary['suid_total_unique']=len(set(x for values in latest.values() for x in values))
    (folder/'catalog-private.json').write_text(json.dumps({kind:[list(x) for x in sorted(values)] for kind,values in sorted(catalog.items())},indent=2)+'\n')
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
    return 0 if summary['qmi_frames'] and not summary['malformed_frames'] and any(catalog.values()) else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    parser.add_argument('--duration',type=float,default=18)
    parser.add_argument('--default',action='store_true')
    args=parser.parse_args()
    if not 5<=args.duration<=30:parser.error('duration must be 5..30 seconds')
    raise SystemExit(run(args))
