#!/usr/bin/env python3
"""Use the RX51 strict Windows reader audit for the RX53 candidate comparison."""
import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib

def stats(line):
    return {k:v if k in {'status','id','after','bad_id'} else int(v)
            for k,v in re.findall(r'([a-z][a-z0-9_]+)=([0-9a-f]+)(?: |$)',line)}

def capture(root,name):
    # Same strict read/queue/framing checks as RX51. Normalize repeated CR
    # before LF too: tty ONLCR output can contain CRCRLF in the original wire.
    raw=(root/(name+'.raw')).read_bytes(); frames=[]; text=bytearray(); pos=0
    while pos<len(raw):
        assert pos+2<=len(raw) and raw[pos]==0x90
        n=raw[pos+1]; assert 1<=n<=4 and pos+n+2<=len(raw)
        frames.append(raw[pos:pos+n+2]); text.extend(raw[pos+2:pos+n+2]); pos+=n+2
    rows=[json.loads(s) for s in (root/(name+'.rx-audit.jsonl')).read_text(encoding='utf-8-sig').splitlines()]
    assert rows[0]['event']=='opened' and rows[-1]['event']=='closed'
    closed=rows[-1]; reads=[r for r in rows if r['event']=='read']; offset=0
    for row in reads:
        assert row['raw_offset']==offset and 0<row['returned']<=row['requested']==row['in_queue']
        offset+=row['returned']
    assert offset==len(raw)==closed['audit']['bytes'] and len(reads)==closed['audit']['reads']
    assert len(frames)==closed['received_frames'] and not closed['serial_is_open'] and closed['probe_detached']
    assert not any(closed[k] for k in ('stray','buffered_bytes','queued_input'))
    assert not any(r['event'] in ('error_sample','error_event') for r in rows) and not closed['audit']['error_mask']
    for field in ('in_queue','read_ms','decode_display_ms'):
        assert max(r[field] for r in reads)==closed['audit']['max_'+field]
    log=(root/(name+'.events.txt')).read_text(encoding='utf-8-sig')
    writes=[dict(ms=int(m[1]),n=int(m[2]),data=bytes.fromhex(m[3]),attempt=int(m[4]),sync=m[5]=='True')
            for m in re.finditer(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)',log)]
    acks=[(int(m[1]),int(m[2]),bytes.fromhex(m[3])) for m in re.finditer(r'(?m)^(\d+) ACK native len=(\d+) data=([0-9a-f ]+)',log)]
    assert all(w['n']==len(w['data']) and w['n'] in (1,*range(3,15)) for w in writes)
    payload=text.decode('ascii'); normalize=lambda s:re.sub(r'\r+\n','\n',s)
    assert normalize((root/(name+'.txt')).read_bytes().decode('utf-8-sig'))==normalize(payload)
    return dict(raw=raw,frames=frames,text=payload,rows=rows,writes=writes,acks=acks,closed=closed,
                summary=dict(bytes=len(raw),frames=len(frames),sha256=sha256(raw).hexdigest(),reads=len(reads),
                             audit=closed['audit'],pending_input=closed['pending_input'],native_frames=closed['native_frames'],
                             retries=closed['retries'],serial_closed=True))

def analyze(root, source):
    assert source.name=='analyze.py' and 'def capture(root, name)' in source.read_text()
    c=capture(root,'windows-overlap-01'); text=c['text']
    assert not c['closed']['pending_input'] and c['closed']['native_frames']==22 and not c['closed']['retries']
    assert [(w['n'],w['data']) for w in c['writes']]==[(n,d) for _,n,d in c['acks']]
    assert len(c['writes'])==23 and all(w['attempt']==1 for w in c['writes'])
    commands=("unset R51H;P=/sys/bus/platform/devices/88e0000.serial;cat $P/rx_stats $P/console_rx\n"
              "printf '<6>R51LOCK:%0990d:R51END\\n' 0 >/dev/kmsg\nR51H=1\n"
              "dd if=$P/tx_journal of=/tmp/R53W1 bs=4096 count=1\nbase64 /tmp/R53W1\n"
              "cat $P/rx_stats $P/console_rx;printf 'R51H=%s\\n' \"$R51H\"\n").encode()
    assert b''.join(w['data'] for w in c['writes'] if not w['sync'])==commands
    assert sum(w['n'] for w in c['writes'])==266 and c['writes'][0]['data']==b'\x15'
    marker,=[r for r in c['rows'] if r['event']=='overlap_marker']; end,=[r for r in c['rows'] if r['event']=='overlap_end']
    probe,=[w for w in c['writes'] if w['data']==b'R51H=1\n']
    receipt,=[ms for ms,n,d in c['acks'] if d==probe['data']]
    assert marker['ms']<probe['ms']<end['ms']<=receipt<probe['ms']+4000
    assert 'eud: rx frame len=7 data=52 35 31 48 3d 31 0a s1_after=06060606 via=console\n' in text
    log,=re.finditer(r'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:(0+):R51END\n',text)
    assert len(log[1])==990 and '\nR51H=1\r\n' in text
    before,after=map(stats,re.findall(r'polls=\d+ pending=\d+ bad=\d+ frames=\d+ f1=\d+.*?console_frames=\d+',text))
    assert (before['frames'],before['bytes'],before['tty'],before['console_frames'])==(32,366,366,1)
    assert (after['frames'],after['bytes'],after['tty'],after['console_frames'])==(48,547,547,2)
    for row in (before,after):
        assert row['frames']==row['irq_frames']+row['poll_frames']+row['console_frames'] and row['active']==1
        assert not any(row[k] for k in ('bad','no_tty','overrun','poll_frames','watchdog','drops','fault','queued'))
    console=list(map(stats,re.findall(r'checks=\d+ frames=\d+ f1=\d+ empty_irqs=\d+ credit=\d+',text)))
    assert console[-1]['frames']==console[-1]['empty_irqs']==2 and not console[-1]['credit']
    assert after['empty']-before['empty']==1
    raw_body=b''.join(f[2:] for f in c['frames'])
    export,=re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',raw_body)
    blob=base64.b64decode(re.sub(rb'\s+',b'',export.group()),validate=True)
    magic,version,size,count,recsize,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
    assert (magic,version,size,count,recsize,reserved)==(b'EUDTXJ48',1,3120,512,6,0) and last-first+1==512
    check=bytearray(blob); check[40:44]=bytes(4); assert zlib.crc32(check)==crc
    wanted=[]
    for i in range(count):
        r=blob[48+6*i:54+6*i]; n,origin=r[:2]
        assert 1<=n<=4 and origin in (1,2) and not any(r[2+n:])
        wanted.append(bytes([0x90,n])+r[2:2+n])
    ends=[]; offset=0
    for f in c['frames']: offset+=len(f)-2; ends.append(offset)
    cutoff=sum(stop<=export.start() for stop in ends)
    start,=[i for i in range(cutoff-511) if c['frames'][i:i+512]==wanted]
    opened=c['rows'][0]
    assert opened['script_sha256']==sha256((root/'eud-console-overlap.ps1').read_bytes()).hexdigest()
    assert opened['probe_sha256']==sha256((root/'EudRxAudit.cs').read_bytes()).hexdigest()
    return dict(c['summary'],data_bytes=265,data_frames=22,all_once_and_receipted=True,
                marker_ms=marker['ms'],probe_ms=probe['ms'],end_ms=end['ms'],receipt_ms=receipt,
                receipt_delay_ms=receipt-probe['ms'],probe_source='console',console_digits=990,
                before=before,after=after,console=console,variable_value='1',
                journal=dict(first_seq=first,last_seq=last,crc=f'{crc:08x}',sha256=sha256(blob).hexdigest(),
                             direct_matching_frames=512,raw_start_frame=start),
                limits='One Windows candidate overlap sample succeeds; no observed driver errors does not exclude other historical TX/reopen loss.'),blob

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); parser.add_argument('--rx51-source',required=True,type=Path); args=parser.parse_args()
    result,blob=analyze(args.root,args.rx51_source)
    (args.root/'windows-success-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (args.root/'windows-tx-journal.bin').write_bytes(blob)
    print(json.dumps({k:result[k] for k in ('bytes','frames','receipt_delay_ms','probe_source','journal')}))
