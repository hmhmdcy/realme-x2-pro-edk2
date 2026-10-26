"""Standard SEE vector streams with explicit attributes, ACK and disable checks."""
import argparse,collections,hashlib,importlib.util,json,math,os,socket,struct,time
from pathlib import Path

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def vector(wire,payload):
    fields=wire.protobuf(payload);status=wire.unique(fields,2,int,0)
    if status not in range(4):raise ValueError('invalid vector accuracy')
    values=[]
    for value,kind in zip(fields.get(1,[]),fields.wires.get(1,[])):
        if kind==5:values.append(struct.unpack('<f',struct.pack('<I',value))[0])
        elif kind==2 and len(value)%4==0:values.extend(struct.unpack('<'+'f'*(len(value)//4),value))
        else:raise ValueError('invalid vector wire encoding')
    if len(values)!=3 or any(not math.isfinite(v) for v in values):raise ValueError('invalid three-axis vector')
    return values,status

def run(args):
    base=Path(__file__).resolve().parent
    light=module(base/'ssc-light-probe.py','light_helpers')
    wire=light.load_wire(base/'ssc-suid-census.py')
    os.umask(0o077);root=Path(args.output);root.mkdir(mode=0o700)
    endpoint,listing=wire.locate_service();(root/'qrtr-private.txt').write_text(listing)
    catalog={};operations={};selected=None;samples=[];attrs={};events=collections.Counter();malformed=[]
    enabled=False;disabled=False;summary={};start=time.monotonic()
    with socket.socket(socket.AF_QIPCRTR,socket.SOCK_DGRAM) as sock,(root/'frames-private.jsonl').open('x') as trace:
        sock.bind((sock.getsockname()[0],0));sock.connect(endpoint);sock.settimeout(.2)
        def send(raw):
            sock.send(raw);trace.write(json.dumps(dict(direction='tx',elapsed=time.monotonic()-start,hex=raw.hex()))+'\n');trace.flush()
        def receive(seconds):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                try:raw,_,flags,_=sock.recvmsg(65536)
                except socket.timeout:continue
                if flags & socket.MSG_TRUNC:raise ValueError('truncated QRTR frame')
                item=dict(direction='rx',elapsed=time.monotonic()-start,hex=raw.hex())
                try:
                    d=wire.decode_frame(raw);item['decoded']=d
                    if 'operation_result' in d:
                        txn=d['transaction']
                        if txn in operations:raise ValueError('duplicate operation ACK')
                        operations[txn]=(d['operation_result'],d['operation_error'])
                    for event in d['events']:
                        events[str(event['message_id'])]+=1
                        if 'suids' in event:catalog[event['data_type']]=[tuple(v) for v in event['suids']]
                        elif selected and tuple(d['sensor_uid'])==selected:
                            if event['message_id']==128:attrs['raw']=event['payload_hex']
                            elif event['message_id']==1025:
                                values,status=vector(wire,bytes.fromhex(event['payload_hex']))
                                samples.append(dict(values=values,accuracy=status,timestamp=event['timestamp'],elapsed=time.monotonic()-start))
                except (ValueError,UnicodeDecodeError,struct.error) as e:
                    item['decode_error']=str(e);malformed.append(str(e))
                trace.write(json.dumps(item)+'\n');trace.flush()
        try:
            send(wire.request(1,args.sensor,False,updates=False));receive(4)
            assert len(catalog.get(args.sensor,[]))==1 and operations.get(1)==(0,0)
            selected=catalog[args.sensor][0]
            send(light.sensor_request(wire,2,selected,1,wire.uint(2,0)));receive(3)
            raw=bytes.fromhex(attrs['raw'])
            available=wire.unique(light.attribute_scalar(wire,raw,3),5,int,0)
            physical=wire.unique(light.attribute_scalar(wire,raw,21),5,int,0)
            stream=wire.unique(light.attribute_scalar(wire,raw,16),4,int,1)
            assert available==physical==1 and stream==0 and operations.get(2)==(0,0)
            send(light.sensor_request(wire,3,selected,513,b'\x0d'+struct.pack('<f',25.0)))
            enabled=True;receive(args.duration)
            summary.update(sensor_available=True,physical_sensor=True,continuous_stream=True,requested_rate_hz=25)
        finally:
            if selected and enabled:
                send(light.sensor_request(wire,4,selected,10));receive(3);disabled=operations.get(4)==(0,0)
            (root/'samples-private.json').write_text(json.dumps(samples,indent=2)+'\n')
            norms=[math.sqrt(sum(v*v for v in s['values'])) for s in samples]
            timestamps=[s['timestamp'] for s in samples]
            summary.update(sensor=args.sensor,samples=len(samples),reliable_samples=sum(s['accuracy']>0 for s in samples),
                malformed_frames=len(malformed),disable_ack=disabled,operations=operations,events=dict(events),
                duration_seconds=round(time.monotonic()-start,3),
                strictly_increasing_sensor_timestamps=bool(timestamps) and all(b>a for a,b in zip(timestamps,timestamps[1:])),
                mean_norm=sum(norms)/len(norms) if norms else None,minimum_norm=min(norms,default=None),maximum_norm=max(norms,default=None),
                success=bool(samples) and disabled and not malformed and operations.get(3)==(0,0))
            (root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
    return 0 if summary['success'] else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--sensor',choices=['accel','gyro','mag'],required=True);parser.add_argument('--duration',type=float,default=10)
    args=parser.parse_args()
    if not 5<=args.duration<=20:parser.error('duration must be 5..20 seconds')
    raise SystemExit(run(args))
