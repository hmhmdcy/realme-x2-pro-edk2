import base64
from collections import Counter
from hashlib import sha256
import gzip
import json
from pathlib import Path
import re
import struct
import zlib

root = Path(__file__).resolve().parent
prefix = root / 'repeated-console-01'
raw = prefix.with_suffix('.raw').read_bytes()
frames, body, ends, p = [], bytearray(), [], 0
while p < len(raw):
    assert raw[p] == 0x90 and 1 <= raw[p+1] <= 4
    n = raw[p+1]
    assert p+n+2 <= len(raw)
    frames.append(raw[p:p+n+2]); body.extend(raw[p+2:p+n+2]); ends.append(len(body)); p += n+2
text = body.decode('ascii')
normalize = lambda s: re.sub(r'\r+\n', '\n', s)
assert normalize(prefix.with_suffix('.txt').read_bytes().decode()) == normalize(text)
events = [json.loads(s) for s in prefix.with_suffix('.events.jsonl').read_text().splitlines()]
meta = json.loads(prefix.with_suffix('.json').read_text())
closed = events[-1]
assert closed['event'] == 'closed' and closed['sink_drained'] and not closed['worker_alive'] and not closed['errors']
assert closed['frames'] == len(frames) and closed['io_bytes'] == len(raw) and not closed['pending'] and not closed['stray']
assert closed['overlap_runs'] == 9 and closed['overlap_receipt'] and closed['synchronized']
assert closed['data_frames'] == closed['acked'] == 70 and closed['data_bytes'] == 806 and closed['steps'] == 14
incoming = [bytes.fromhex(e['hex']) for e in events if e['event'] == 'in']
writes = [e for e in events if e['event'] == 'out_submit']
acks = [e for e in events if e['event'] == 'receipt']
assert b''.join(incoming) == raw
assert len(writes) == len(acks) == 71
assert [(e['length'],e['payload_hex'],e['sync']) for e in writes] == [(e['length'],e['payload_hex'],e['sync']) for e in acks]
assert all(e['attempt'] == 1 and e['length'] in (1,*range(3,15)) for e in writes)
assert not any(e['event'] == 'receipt_timeout' for e in events)
assert [e['index'] for e in events if e['event'] == 'overlap_armed'] == list(range(1,10))
markers = [e for e in events if e['event'] == 'overlap_marker']
ending = [e for e in events if e['event'] == 'overlap_end']
logs = list(re.finditer(r'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:(0+):R51END\n', text))
assert len(markers) == len(ending) == len(logs) == 9
probes = []
for i in range(1,10):
    payload = ('R54H%02d=1\n' % i).encode()
    write, = [e for e in writes if bytes.fromhex(e['payload_hex']) == payload]
    ack, = [e for e in acks if bytes.fromhex(e['payload_hex']) == payload]
    marker, end = markers[i-1], ending[i-1]
    assert marker['ms'] < write['ms'] < end['ms'] < ack['ms'] < write['ms']+4000
    assert re.search(r'eud: rx frame len=9 data=' + re.escape(payload.hex(' ')) + r' s1_after=06060606 via=console\n', text)
    assert len(logs[i-1][1]) == 990
    probes.append(dict(index=i, marker_ms=marker['ms'], probe_ms=write['ms'], end_ms=end['ms'],
                       receipt_ms=ack['ms'], marker_to_probe_ms=round(write['ms']-marker['ms'],3),
                       receipt_delay_ms=round(ack['ms']-write['ms'],3), digits=990, source='console'))
assert '\nR54V=111111111\r\n' in text
def fields(line):
    return {k:v if k in {'status','id','after','bad_id'} else int(v)
            for k,v in re.findall(r'([a-z][a-z0-9_]+)=([0-9a-f]+)(?: |$)', line)}
before, after = map(fields, re.findall(r'polls=\d+ pending=\d+ bad=\d+ frames=\d+ f1=\d+.*?console_frames=\d+', text))
assert (before['frames'],before['bytes'],before['tty'],before['console_frames']) == (25,247,247,0)
assert (after['frames'],after['bytes'],after['tty'],after['console_frames']) == (87,967,967,9)
for row in (before,after):
    assert row['frames'] == row['irq_frames']+row['poll_frames']+row['console_frames'] and row['active'] == 1
    assert not any(row[k] for k in ('bad','overrun','no_tty','poll_frames','watchdog','drops','fault','queued'))
console = list(map(fields, re.findall(r'checks=\d+ frames=\d+ f1=\d+ empty_irqs=\d+ credit=\d+', text)))
assert console[-1]['frames'] == 9 and console[-1]['empty_irqs'] == 6 and console[-1]['credit'] == 0
assert after['empty']-before['empty'] == 6
assert text.count('waits=0 recovered=0 cleared=0 waiting=0 max_ms=0 first=00 last=00 err=0') == 2
ins, outs, done, pending, statuses, partial = [], [], [], {}, Counter(), []
trace_path = prefix.with_suffix('.usbmon')
trace = trace_path.read_bytes() if trace_path.exists() else gzip.decompress(prefix.with_suffix('.usbmon.gz').read_bytes())
for line in trace.decode().splitlines():
    f = line.split(); addr = f[3].split(':')
    assert tuple(map(int,addr[1:3])) == (meta['bus'],meta['address'])
    direction = addr[0]; assert direction in ('Bi','Bo') and int(addr[3]) == (1 if direction == 'Bi' else 2)
    status, n = int(f[4]), int(f[5])
    data = bytes.fromhex(''.join(f[7:])) if len(f)>6 and f[6] == '=' else b''
    if direction == 'Bi' and f[2] == 'C':
        statuses[str(status)] += 1
        if n:
            assert status in (0,-2) and len(data) == n <= 16
            ins.append(data)
            if status: partial.append(dict(status=status,bytes=n,hex=data.hex(' ')))
    elif direction == 'Bo':
        if f[2] == 'S':
            assert len(data) == n <= 16 and f[0] not in pending
            pending[f[0]] = data; outs.append(data)
        else:
            sent = pending.pop(f[0]); assert status == 0 and n == len(sent); done.append(n)
assert not pending and ins == incoming == frames and b''.join(ins) == raw
assert outs == [bytes.fromhex(e['hex']) for e in writes] and done == list(map(len,outs))
export, = re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*', body)
blob = base64.b64decode(re.sub(rb'\s+',b'',export.group()), validate=True)
magic,version,size,count,record_size,first,last,crc,reserved = struct.unpack_from('<8sIIIIQQII', blob)
assert (magic,version,size,count,record_size,reserved) == (b'EUDTXJ48',1,3120,512,6,0) and last-first+1 == 512
check = bytearray(blob); check[40:44] = bytes(4); assert zlib.crc32(check) == crc
wanted = []
for i in range(count):
    r = blob[48+6*i:54+6*i]; n, source = r[:2]
    assert 1 <= n <= 4 and source in (1,2) and not any(r[2+n:])
    wanted.append(bytes([0x90,n])+r[2:2+n])
cutoff = sum(stop <= export.start() for stop in ends)
start, = [i for i in range(cutoff-511) if frames[i:i+512] == wanted]
summary = dict(raw_bytes=len(raw),raw_frames=len(frames),raw_sha256=sha256(raw).hexdigest(),
               usbmon_sha256=sha256(trace).hexdigest(),in_statuses=dict(statuses),partial_cancels=partial,
               full_in_equals_raw=True,out_count=len(outs),all_out_completed_once_and_receipted=True,
               probes=probes,before=before,after=after,console=console,variable_readback='111111111',closed=closed,
               journal=dict(first_seq=first,last_seq=last,crc=f'{crc:08x}',sha256=sha256(blob).hexdigest(),
                            direct_matching_frames=512,raw_start_frame=start),
               limits='Nine manual overlaps pass, with six credited empty IRQ observations; eight consecutive empty IRQs were not induced. Physical USB ACK and global TX/reopen stability remain unproven.')
if __name__ == '__main__':
    (root/'repeat-tx-journal.bin').write_bytes(blob)
    (root/'repeat-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
