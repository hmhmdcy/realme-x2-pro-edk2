#!/usr/bin/env python3
"""Strict three-owner comparison of the final first-status issued frame loss."""
import argparse
import base64
from collections import Counter
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib

def decode(root,name):
    raw=(root/(name+'.raw')).read_bytes(); frames=[]; body=bytearray(); pos=0
    while pos<len(raw):
        assert raw[pos]==0x90 and pos+2<=len(raw)
        n=raw[pos+1]; assert 1<=n<=4 and pos+n+2<=len(raw)
        frames.append(raw[pos:pos+n+2]); body.extend(raw[pos+2:pos+n+2]); pos+=n+2
    # Passive boot includes UTF-8 bytes; the existing .NET ASCII decoder maps
    # each non-ASCII byte to '?'. Raw frame accounting remains byte-exact.
    decoded=body.decode('ascii',errors='replace').replace('\ufffd','?')
    normalize=lambda s: re.sub(r'\r+\n','\n',s)
    assert normalize((root/(name+'.txt')).read_bytes().decode('utf-8-sig'))==normalize(decoded)
    return raw,frames,body

def analyze(root):
    boot,boot_frames,_=decode(root,'candidate-final-boot')
    missing,mid_frames,mid_body=decode(root,'installed-final-native')
    raw,post_frames,body=decode(root,'post-final-journal')
    assert mid_body.startswith(b'95.409512] eud: tty byte=15') and len(mid_frames)==87
    assert b'\r\nR53END1\r\n' in mid_body
    event_text=(root/'installed-final-native.events.txt').read_text(encoding='utf-8-sig')
    assert 'TX native len=1 data=15 attempt=1 sync=True' in event_text
    assert 'TX native len=13 data=65 63 68 6f 20 52 35 33 45 4e 44 31 0a attempt=1 sync=False' in event_text
    assert len(re.findall(r'(?m)^\d+ TX native',event_text))==len(re.findall(r'(?m)^\d+ ACK native',event_text))==2
    events=[json.loads(s) for s in (root/'post-final-journal.events.jsonl').read_text().splitlines()]
    closed=events[-1]; assert closed['event']=='closed' and closed['sink_drained'] and not closed['worker_alive'] and not closed['errors']
    assert closed['io_bytes']==len(raw) and closed['frames']==len(post_frames) and not closed['stray'] and not closed['pending']
    assert closed['data_frames']==closed['acked']==13 and closed['data_bytes']==145 and closed['steps']==4
    ins=[bytes.fromhex(e['hex']) for e in events if e['event']=='in']
    outs=[bytes.fromhex(e['hex']) for e in events if e['event']=='out_submit']
    acks=[e for e in events if e['event']=='receipt']
    assert len(outs)==len(acks)==14 and b''.join(ins)==raw and ins==post_frames
    assert all(e['attempt']==1 for e in events if e['event']=='out_submit')
    path=root/'post-final-journal.usbmon'
    trace=path.read_bytes() if path.exists() else gzip.decompress((root/'post-final-journal.usbmon.gz').read_bytes())
    meta=json.loads((root/'post-final-journal.json').read_text()); usb_ins=[]; usb_outs=[]; pending={}; statuses=Counter()
    for line in trace.decode('ascii').splitlines():
        f=line.split(); addr=f[3].split(':'); direction=addr[0]
        assert tuple(map(int,addr[1:3]))==(meta['bus'],meta['address']) and direction in ('Bi','Bo')
        assert int(addr[3])==(1 if direction=='Bi' else 2) and f[2] in ('S','C')
        status,n=int(f[4]),int(f[5]); data=bytes.fromhex(''.join(f[7:])) if len(f)>6 and f[6]=='=' else b''
        if direction=='Bi' and f[2]=='C':
            statuses[str(status)]+=1
            if n: assert len(data)==n<=16 and status in (0,-2); usb_ins.append(data)
        elif direction=='Bo':
            if f[2]=='S': assert len(data)==n<=16; pending[f[0]]=data; usb_outs.append(data)
            else: assert status==0 and n==len(pending.pop(f[0]))
    assert not pending and usb_ins==ins and usb_outs==outs
    export,=re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',body)
    blob=base64.b64decode(re.sub(rb'\s+',b'',export.group()),validate=True)
    magic,version,size,count,recsize,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
    assert (magic,version,size,count,recsize,reserved)==(b'EUDTXJ48',1,3120,512,6,0) and last-first+1==count
    check=bytearray(blob); check[40:44]=bytes(4); assert zlib.crc32(check)==crc
    records=[blob[48+6*i:54+6*i] for i in range(count)]; wanted=[]
    for r in records:
        n,origin=r[:2]; assert 1<=n<=4 and origin in (1,2) and not any(r[2+n:]); wanted.append(bytes([0x90,n])+r[2:2+n])
    start,=[i for i in range(count-len(mid_frames)) if wanted[i+1:i+1+len(mid_frames)]==mid_frames]
    assert wanted[start]==bytes.fromhex('90 04 5b 20 20 20') and records[start][1]==2
    assert boot_frames[-start:]==wanted[:start]
    tail=start+1+len(mid_frames); assert post_frames[:count-tail]==wanted[tail:]
    assert b''.join(wanted[start:start+8][i][2:] for i in range(8)).startswith(b'[   95.409512] eud: tty byte=15')
    result=dict(missing_seq=first+start,missing_wire=wanted[start].hex(' '),missing_text='[   ',
                missing_source='console',before_owner_matched=start,affected_owner_matched=len(mid_frames),
                recovery_owner_matched=count-tail,direct_matches=count-1,journal_first=first,journal_last=last,
                journal_crc=f'{crc:08x}',journal_sha256=sha256(blob).hexdigest(),
                affected_raw_sha256=sha256(missing).hexdigest(),recovery_raw_bytes=len(raw),
                recovery_raw_frames=len(post_frames),full_recovery_in_equals_raw=True,in_statuses=dict(statuses),
                command_and_receipts_complete=True,closed=closed,
                limits='One issued four-byte prefix is absent at its exact position in installed Windows terminal raw. EUD TX/physical USB/Windows receive stage remains unresolved; this does not invalidate the separately verified busy-console RX improvement.')
    return result,blob

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); args=parser.parse_args()
    result,blob=analyze(args.root)
    (args.root/'final-tx-loss-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.root/'final-tx-journal.bin').write_bytes(blob)
    print(json.dumps({k:result[k] for k in ('missing_seq','missing_wire','direct_matches','before_owner_matched','affected_owner_matched','recovery_owner_matched','journal_crc')}))
