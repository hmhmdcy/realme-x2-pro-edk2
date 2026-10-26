from collections import Counter
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parent
prefix = root/'console-f1-01'
raw = prefix.with_suffix('.raw').read_bytes()
frames, body, p = [], bytearray(), 0
while p < len(raw):
    assert raw[p] == 0x90 and 1 <= raw[p+1] <= 4
    n = raw[p+1]; assert p+n+2 <= len(raw)
    frames.append(raw[p:p+n+2]); body.extend(raw[p+2:p+n+2]); p += n+2
text = body.decode()
norm = lambda s: re.sub(r'\r+\n','\n',s)
assert norm(prefix.with_suffix('.txt').read_bytes().decode()) == norm(text)
events = [json.loads(s) for s in prefix.with_suffix('.events.jsonl').read_text().splitlines()]
meta = json.loads(prefix.with_suffix('.json').read_text())
closed = events[-1]
assert closed['event'] == 'closed' and not closed['worker_alive'] and not closed['errors'] and closed['sink_drained']
assert closed['frames'] == len(frames) and closed['io_bytes'] == len(raw) and not closed['pending'] and not closed['stray']
assert closed['f1_submitted'] and closed['f1_disconnect'] and closed['f1_console_receipt']
assert closed['data_frames'] == closed['acked'] == 4 and closed['data_bytes'] == 49 and closed['steps'] == 2
data = [e for e in events if e['event'] == 'out_submit']
acks = [e for e in events if e['event'] == 'receipt']
assert len(data) == len(acks) == 5 and all(e['attempt'] == 1 for e in data)
assert [(e['length'],e['payload_hex'],e['sync']) for e in data] == [(e['length'],e['payload_hex'],e['sync']) for e in acks]
expected = b"printf '<6>R51LOCK:%0990d:R51END\\n' 0 >/dev/kmsg\n"
assert b''.join(bytes.fromhex(e['payload_hex']) for e in data if not e['sync']) == expected
f1, = [e for e in events if e['event'] == 'f1_out_submit']
complete, = [e for e in events if e['event'] == 'f1_out_complete']
assert f1['hex'] == '90 02' and f1['attempt'] == 1 and not f1['payload_bytes'] and complete['length'] == 2
marker, = [e for e in events if e['event'] == 'overlap_marker']
end, = [e for e in events if e['event'] == 'overlap_end']
assert marker['ms'] < f1['ms'] < complete['ms'] < end['ms']
log, = re.finditer(r'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:(0+):R51END\n',text)
assert len(log[1]) == 990
assert 'eud: RX46 F1 via=console irqs=90 fault=0\n' in text and 'eud: reboot2 bootloader requested\n' in text
assert not any(e['event'] == 'receipt_timeout' for e in events)
incoming = [bytes.fromhex(e['hex']) for e in events if e['event'] == 'in']
assert b''.join(incoming) == raw
path = prefix.with_suffix('.usbmon')
trace = path.read_bytes() if path.exists() else gzip.decompress(prefix.with_suffix('.usbmon.gz').read_bytes())
ins, outs, pending, statuses = [], [], {}, Counter()
for line in trace.decode().splitlines():
    f = line.split(); addr = f[3].split(':')
    assert tuple(map(int,addr[1:3])) == (meta['bus'],meta['address'])
    direction = addr[0]; assert direction in ('Bi','Bo') and int(addr[3]) == (1 if direction == 'Bi' else 2)
    status,n = int(f[4]),int(f[5]); content = bytes.fromhex(''.join(f[7:])) if len(f)>6 and f[6] == '=' else b''
    if direction == 'Bi' and f[2] == 'C':
        statuses[str(status)] += 1
        if n:
            assert status in (0,-2) and n == len(content) <= 16
            ins.append(content)
    elif direction == 'Bo':
        if f[2] == 'S':
            assert len(content) == n <= 16 and f[0] not in pending
            outs.append(content); pending[f[0]] = content
        else:
            sent = pending.pop(f[0]); assert status == 0 and n == len(sent)
assert not pending and ins == incoming == frames and b''.join(ins) == raw
assert outs == [bytes.fromhex(e['hex']) for e in events if e['event'] in ('out_submit','f1_out_submit')]
assert len(outs) == 6 and outs[-1] == b'\x90\x02'
fastboot = (root/'f1-fastboot.txt').read_text()
assert re.search(r'^62bc28a1\s+fastboot$',fastboot,re.M) and 'product: msmnile' in fastboot
reboot = (root/'same-image-reboot.txt').read_text(); assert 'Rebooting' in reboot and 'OKAY' in reboot
summary = dict(raw_bytes=len(raw),frames=len(frames),raw_sha256=sha256(raw).hexdigest(),
               in_statuses=dict(statuses),full_in_equals_raw=True,out_count=len(outs),all_out_once_completed=True,
               f1_hex='90 02',f1_source='console',f1_payload_bytes=0,marker_ms=marker['ms'],f1_ms=f1['ms'],end_ms=end['ms'],
               marker_to_f1_ms=round(f1['ms']-marker['ms'],3),console_digits=990,fastboot_serial='62bc28a1',product='msmnile',closed=closed,
               limits='USB I/O failure follows the accepted F1, with a separate fastboot check. Detach sees the former bus node removed. No flash; physical USB ACK and remaining TX loss are unmeasured.')
if __name__ == '__main__':
    (root/'f1-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
