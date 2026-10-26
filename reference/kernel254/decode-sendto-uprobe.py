"""Decode bounded read-only sendto uprobe snapshots, keeping payloads private.

The capture stores at most 256 bytes. A larger send is retained as a prefix,
never parsed as a complete QMI message or claimed to have succeeded. Compare
against strace successful sends before relying on the entry probe.
"""
from pathlib import Path
import importlib.util
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire250',ROOT/'kernel250/decode-android-hal.py')
wire=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)
META=re.compile(r'-(\d+)\s+\[\d+\].*?\s(\d+\.\d+): sendto:')
RETURN_META=re.compile(r'-(\d+)\s+\[\d+\].*?\s(\d+\.\d+): sendto_ret:')
FIELDS=re.compile(r'([A-Za-z][A-Za-z0-9_]*)=(0x[0-9a-f]+|-?[0-9]+)')


def decode(path):
    events=[]
    pending={}
    for line in Path(path).read_text().splitlines():
        returned=RETURN_META.search(line)
        if returned:
            tid=int(returned[1])
            if pending.get(tid):
                event=pending[tid].pop()
                fields=dict(FIELDS.findall(line))
                event.update(result=int(fields['result'],0),return_boot_time=float(returned[2]))
            continue
        if 'sendto:' not in line: continue
        match=META.search(line)
        if not match: raise ValueError('Unexpected uprobe metadata')
        fields=dict(FIELDS.findall(line))
        if not all('w'+str(i) in fields for i in range(32)):
            raise ValueError('Missing/faulted payload snapshot word')
        size=int(fields['size'],0)
        raw=b''.join(int(fields['w'+str(i)],0).to_bytes(8,'little') for i in range(32))[:size]
        complete=size<=256
        packet=None
        if complete:
            try: packet=wire.decode_wire(raw)
            except ValueError: pass
        events.append(dict(tid=int(match[1]),boot_time=float(match[2]),
                           fd=int(fields['fd'],0),size=size,
                           family=int(fields['peer0'],0)&0xffff,
                           peer_node=int(fields['peer0'],0)>>32,
                           peer_port=int(fields['peer1'],0),
                           prefix_hex=raw.hex(),complete_snapshot=complete,
                           packet=packet))
        pending.setdefault(int(match[1]),[]).append(events[-1])
    return events
