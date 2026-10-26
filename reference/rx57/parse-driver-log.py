from pathlib import Path
from hashlib import sha256
import argparse,json,struct
from datetime import datetime,timedelta,timezone

def parse(path):
    data=path.read_bytes(); records=[];offset=0;issue=None;wire=bytearray()
    while offset<len(data):
        if len(data)-offset<13:
            issue=dict(offset=offset,reason='partial 13-byte header',remaining=len(data)-offset);break
        ticks,kind,length=struct.unpack_from('<QBI',data,offset)
        if length>1048576:
            issue=dict(offset=offset,reason='unreasonable length',length=length);break
        if offset+13+length>len(data):
            issue=dict(offset=offset,reason='partial body',declared=length,remaining=len(data)-offset-13);break
        payload=data[offset+13:offset+13+length]
        try: stamp=(datetime(1601,1,1,tzinfo=timezone.utc)+timedelta(microseconds=ticks//10)).isoformat()
        except OverflowError: stamp=None
        records.append(dict(offset=offset,filetime_ticks=ticks,utc_microsecond_precision=stamp,type=kind,length=length,payload_hex=payload.hex()))
        # The exact RX worker passes type 0; QCSER_LogData can mark it 5.
        # Do not treat error/status/other types as wire data.
        if kind in (0,5):wire.extend(payload)
        offset+=13+length
    return dict(source=str(path),sha256=sha256(data).hexdigest(),file_bytes=len(data),complete=(issue is None),issue=issue,records=records,successful_read_bytes=len(wire),successful_read_sha256=sha256(wire).hexdigest()),bytes(wire)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result,wire=parse(args.input)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/(args.input.name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    (args.out/(args.input.name+'.read.raw')).write_bytes(wire)
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
