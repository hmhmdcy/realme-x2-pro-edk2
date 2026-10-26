#!/usr/bin/env python3
"""Audit the RX53 same-trigger result against full target USB bytes and counters."""
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

def fields(line):
    return {k: v if k in {'status','id','after','bad_id'} else int(v)
            for k,v in re.findall(r'([a-z][a-z0-9_]+)=([0-9a-f]+)(?: |$)',line)}

def analyze(root):
    name = 'console-rx-overlap-01'
    raw = (root/(name+'.raw')).read_bytes()
    frames, body, ends, p = [], bytearray(), [], 0
    while p<len(raw):
        assert p+2<=len(raw) and raw[p]==0x90
        n=raw[p+1]; assert 1<=n<=4 and p+n+2<=len(raw)
        frames.append(raw[p:p+n+2]); body.extend(raw[p+2:p+n+2]); ends.append(len(body)); p+=n+2
    text=body.decode('ascii')
    normalize=lambda s: re.sub(r'\r+\n','\n',s)
    assert normalize((root/(name+'.txt')).read_bytes().decode('utf-8-sig'))==normalize(text)
    meta=json.loads((root/(name+'.json')).read_text())
    events=[json.loads(s) for s in (root/(name+'.events.jsonl')).read_text().splitlines()]
    closed=events[-1]
    assert closed['event']=='closed' and closed['sink_drained'] and not closed['worker_alive'] and not closed['errors']
    assert closed['frames']==len(frames) and closed['io_bytes']==len(raw) and not closed['stray'] and not closed['pending']
    assert closed['overlap_receipt'] and closed['data_frames']==closed['acked']==24 and closed['data_bytes']==280
    assert closed['steps']==6 and closed['synchronized']
    incoming=[bytes.fromhex(e['hex']) for e in events if e['event']=='in']
    writes=[e for e in events if e['event']=='out_submit']
    acks=[e for e in events if e['event']=='receipt']
    assert b''.join(incoming)==raw and len(writes)==len(acks)==25
    assert [(e['length'],e['payload_hex'],e['sync']) for e in writes]==[(e['length'],e['payload_hex'],e['sync']) for e in acks]
    assert all(e['attempt']==1 and e['length'] in (1,*range(3,15)) for e in writes)
    assert not any(e['event']=='receipt_timeout' for e in events)
    expected=("P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/irq_watch $P/console_rx\n"
              "printf '<6>R51LOCK:%0990d:R51END\\n' 0 >/dev/kmsg\nR51H=1\n"
              "dd if=$P/tx_journal of=/tmp/R53J1 bs=4096 count=1\nbase64 /tmp/R53J1\n"
              "cat $P/rx_stats $P/console_rx $P/irq_watch;printf 'R51H=%s\\n' \"$R51H\"\n").encode()
    assert b''.join(bytes.fromhex(e['payload_hex']) for e in writes if not e['sync'])==expected
    probe,=[e for e in writes if e['payload_hex']=='52 35 31 48 3d 31 0a']
    receipt,=[e for e in acks if e['payload_hex']==probe['payload_hex']]
    marker,=[e for e in events if e['event']=='overlap_marker']; end,=[e for e in events if e['event']=='overlap_end']
    assert marker['ms']<probe['ms']<end['ms']<receipt['ms']<probe['ms']+4000
    assert re.search(r'eud: rx frame len=7 data=52 35 31 48 3d 31 0a s1_after=06060606 via=console\n',text)
    match,=re.finditer(r'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:(0+):R51END\n',text)
    assert len(match[1])==990 and '\nR51H=1\r\n' in text
    rows=re.findall(r'polls=\d+ pending=\d+ bad=\d+ frames=\d+ f1=\d+.*?console_frames=\d+',text)
    before,after=map(fields,rows)
    assert (before['frames'],before['bytes'],before['tty'],before['console_frames'])==(9,87,87,0)
    assert (after['frames'],after['bytes'],after['tty'],after['console_frames'])==(25,281,281,1)
    for row in (before,after):
        assert row['frames']==row['irq_frames']+row['poll_frames']+row['console_frames'] and row['active']==1
        assert not any(row[k] for k in ('bad','overrun','no_tty','poll_frames','watchdog','drops','fault','queued'))
    console=list(map(fields,re.findall(r'checks=\d+ frames=\d+ f1=\d+ empty_irqs=\d+ credit=\d+',text)))
    assert console[-1]['frames']==console[-1]['empty_irqs']==1 and console[-1]['credit']==0
    assert after['empty']-before['empty']==1
    assert text.count('waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0')==2

    path=root/(name+'.usbmon')
    trace=path.read_bytes() if path.exists() else gzip.decompress((root/(name+'.usbmon.gz')).read_bytes())
    ins,outs,done,pending=[],[],[],{}
    statuses=Counter(); partial_cancels=[]
    for line in trace.decode('ascii').splitlines():
        f=line.split(); addr=f[3].split(':')
        assert tuple(map(int,addr[1:3]))==(meta['bus'],meta['address'])
        direction=addr[0]; assert direction in ('Bi','Bo') and int(addr[3])==(1 if direction=='Bi' else 2)
        assert f[2] in ('S','C')
        status,n=int(f[4]),int(f[5]); data=bytes.fromhex(''.join(f[7:])) if len(f)>6 and f[6]=='=' else b''
        if direction=='Bi' and f[2]=='C':
            statuses[str(status)]+=1
            if n:
                assert status in (0,-2) and len(data)==n<=16
                if status:
                    partial_cancels.append(dict(status=status,bytes=n,hex=data.hex(' ')))
                ins.append(data)
        elif direction=='Bo':
            if f[2]=='S':
                assert len(data)==n<=16 and f[0] not in pending
                pending[f[0]]=data; outs.append(data)
            else:
                sent=pending.pop(f[0]); assert status==0 and n==len(sent); done.append(n)
    assert not pending and ins==incoming==frames and b''.join(ins)==raw
    assert outs==[bytes.fromhex(e['hex']) for e in writes] and done==list(map(len,outs))

    export,=re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',body)
    blob=base64.b64decode(re.sub(rb'\s+',b'',export.group()),validate=True)
    magic,version,size,count,record_size,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
    assert (magic,version,size,count,record_size,reserved)==(b'EUDTXJ48',1,3120,512,6,0) and last-first+1==512
    check=bytearray(blob); check[40:44]=bytes(4); assert zlib.crc32(check)==crc
    wanted=[]
    for i in range(count):
        r=blob[48+6*i:54+6*i]; n,source=r[:2]
        assert 1<=n<=4 and source in (1,2) and not any(r[2+n:])
        wanted.append(bytes([0x90,n])+r[2:2+n])
    cutoff=sum(stop<=export.start() for stop in ends)
    starts=[i for i in range(cutoff-511) if frames[i:i+512]==wanted]
    start,=starts
    return dict(raw_bytes=len(raw),raw_frames=len(frames),raw_sha256=sha256(raw).hexdigest(),
                usbmon_sha256=sha256(trace).hexdigest(),in_statuses=dict(statuses),partial_cancels=partial_cancels,full_in_equals_raw=True,
                out_count=len(outs),out_full_success=True,all_once_and_receipted=True,
                marker_ms=marker['ms'],probe_ms=probe['ms'],end_ms=end['ms'],receipt_ms=receipt['ms'],
                receipt_delay_ms=round(receipt['ms']-probe['ms'],3),probe_source='console',console_digits=990,
                before=before,after=after,console=console,variable_value='1',closed=closed,
                journal=dict(first_seq=first,last_seq=last,crc=f'{crc:08x}',sha256=sha256(blob).hexdigest(),
                             direct_matching_frames=512,raw_start_frame=start),
                limits='One same-trigger candidate sample succeeds. Physical USB ACK and actual IRQ latency are unmeasured; historical reopen and TX issues still require independent checks.'),blob

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); args=parser.parse_args()
    result,blob=analyze(args.root)
    (args.root/'usb-success-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.root/'usb-tx-journal.bin').write_bytes(blob)
    print(json.dumps({k:result[k] for k in ('raw_bytes','raw_frames','receipt_delay_ms','probe_source','journal')}))
