"""RX55: same-owner Windows counter/raw/journal comparison, without interpolation."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib

def decode(path):
    raw=path.read_bytes(); frames=[]; body=bytearray(); pos=0
    while pos<len(raw):
        assert pos+2<=len(raw) and raw[pos]==0x90
        n=raw[pos+1]; assert 1<=n<=4 and pos+n+2<=len(raw)
        frames.append(raw[pos:pos+n+2]); body.extend(raw[pos+2:pos+n+2]); pos+=n+2
    return raw,frames,bytes(body)

def analyze(root):
    raw,frames,body=decode(root/'windows-perf-01.raw')
    norm=lambda s:re.sub(r'\r+\n','\n',s)
    assert norm(body.decode('utf-8'))==norm((root/'windows-perf-01.txt').read_bytes().decode('utf-8-sig'))
    audit=[json.loads(s) for s in (root/'windows-perf-01.rx-audit.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    opened=audit[0]; closed=audit[-1]
    assert opened['event']=='opened' and closed['event']=='closed'
    assert opened['assembly_sha256']=='2b3c17c6208a0b4b6beb94e1a066f99ba06cdb2ea919479e99d47e8c6d96dc71'
    assert opened['perf_ioctl']==0x1b008c and opened['overlap_size']==32 and opened['overlap_event_offset']==24 and opened['perf_own_event_low_bit']
    assert opened['script_sha256']==sha256((root/'eud-terminal-rx-perf.ps1').read_bytes()).hexdigest()
    assert opened['probe_sha256']==sha256((root/'EudRxAudit.cs').read_bytes()).hexdigest()
    assert opened['perf_probe_sha256']==sha256((root/'EudSerialPerf.cs').read_bytes()).hexdigest()
    assert not closed['serial_is_open'] and closed['probe_detached'] and closed['perf_probe_disposed'] and not closed['retained_pending_perf']
    assert not closed['stray'] and not closed['buffered_bytes'] and not closed['pending_input'] and not closed['queued_input']
    assert closed['received_frames']==len(frames) and closed['audit']['bytes']==len(raw)
    assert not closed['audit']['error_mask'] and not closed['audit']['error_events'] and not closed['audit']['error_samples']
    assert not any(e['event'] in ('perf_error','error_sample','error_event','perf_manual_rejected') for e in audit)
    reads=[e for e in audit if e['event']=='read']; offset=0
    for e in reads:
        assert e['raw_offset']==offset and e['returned']==e['requested']==e['in_queue'] and not e['errors']
        offset+=e['returned']
    assert offset==len(raw) and len(reads)==closed['audit']['reads']
    samples=[e for e in audit if e['event']=='perf']
    assert samples[0]['reason']=='opened-before-sync' and samples[-1]['reason']=='before-close'
    assert samples[0]['raw_position']==0 and samples[-1]['raw_position']==len(raw)
    for e in samples:
        p=e['perf']; assert p['returned']==24
        fields=struct.unpack('<6I',bytes.fromhex(p['raw_hex']))
        assert fields==(p['received'],p['transmitted'],p['frame_errors'],p['serial_overruns'],p['buffer_overruns'],p['parity_errors'])
        assert not any(fields[2:]) and not any(e['queue'].values()) and not e['buffered_wire'] and not e['pending_input']
    deltas=[]
    for a,b in zip(samples,samples[1:]):
        received=(b['perf']['received']-a['perf']['received'])&0xffffffff
        saved=b['raw_position']-a['raw_position']; assert received==saved
        deltas.append(dict(from_ms=a['ms'],to_ms=b['ms'],received_delta=received,raw_delta=saved))
    received=(samples[-1]['perf']['received']-samples[0]['perf']['received'])&0xffffffff
    assert received==len(raw)
    events=(root/'windows-perf-01.events.txt').read_text(encoding='utf-8-sig')
    tx=re.findall(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)$',events)
    acks=re.findall(r'(?m)^(\d+) ACK native len=(\d+) data=([0-9a-f ]+)$',events)
    outs=[]; data=[]; sync=[]
    for ms,n,h,attempt,is_sync in tx:
        payload=bytes.fromhex(h); assert len(payload)==int(n) and int(n)!=2
        outs.append(bytes([0x90,int(n)])+payload)
        (sync if is_sync=='True' else data).append((int(ms),payload,int(attempt)))
    assert len(sync)==2 and sync[0][1:]==(b'\x15',1) and sync[1][1:]==(b'\x15',2)
    assert len(data)==closed['native_frames'] and all(attempt==1 for _,_,attempt in data)
    assert [bytes.fromhex(h) for _,_,h in acks]==[b'\x15']+[p for _,p,_ in data]
    transmitted=(samples[-1]['perf']['transmitted']-samples[0]['perf']['transmitted'])&0xffffffff
    assert transmitted==sum(map(len,outs))
    command_bytes=b''.join(p for _,p,_ in data)
    commands=command_bytes.decode('ascii').splitlines()
    assert len(commands)==4 and commands[0].startswith('P=/sys/class/tty/ttyEUD0/device;dd ')
    assert commands[1].startswith('P=/sys/bus/platform/devices/88e0000.serial;dd ')
    assert commands[2]=='base64 /tmp/R55J' and commands[3]=='cat $P/rx_stats $P/irq_watch $P/console_rx'
    assert b"dd: can't open '/sys/class/tty/ttyEUD0/device/tx_journal': No such file or directory" in body
    export,=re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',body)
    blob=base64.b64decode(re.sub(rb'\s+',b'',export.group()),validate=True)
    magic,version,size,count,recsize,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
    assert (magic,version,size,count,recsize,reserved)==(b'EUDTXJ48',1,3120,512,6,0) and last-first+1==count
    check=bytearray(blob); check[40:44]=bytes(4); assert zlib.crc32(check)==crc
    records=[blob[48+6*i:54+6*i] for i in range(count)]; wanted=[]
    for r in records:
        n,source=r[:2]; assert 1<=n<=4 and source in (1,2) and not any(r[2+n:])
        wanted.append(bytes([0x90,n])+r[2:2+n])
    start,=[k for k in range(count-20) if wanted[k+1:k+21]==frames[:20]]
    assert wanted[start]==bytes.fromhex('90 04 5b 20 31 36') and records[start][1]==2
    assert frames[:count-start-1]==wanted[start+1:]
    previous=root.parent/'rx54'/'restored-native.raw'
    if not previous.exists(): previous=root.parent/'rx54'/'restored-native.raw'
    _,before_frames,_=decode(previous)
    assert before_frames[-start:]==wanted[:start]
    assert body.startswith(b'88.479011] eud: tty byte=15 polls=68870 pending=3 bad=0 frames=3 bytes=16 ')
    assert b'frames=22 f1=0 bytes=249 tty=249' in body and b'fault=0 active=1 queued=0 console_frames=0' in body
    # RX54 left two accepted frames. One of the two new startup Ctrl-U writes
    # adds one frame; all nineteen once-only data frames account for the rest.
    assert 2+1+len(data)==22 and len(data)==19
    first_status_raw=samples[1]['raw_position']; assert first_status_raw==309
    summary=dict(raw_bytes=len(raw),raw_frames=len(frames),read_calls=len(reads),perf_samples=len(samples),
        first_received=samples[0]['perf']['received'],last_received=samples[-1]['perf']['received'],
        received_delta=received,transmitted_delta=transmitted,submitted_wire_bytes=sum(map(len,outs)),
        all_drained_received_deltas_equal_raw=True,drained_deltas=deltas,
        first_status_raw_bytes=first_status_raw,first_status_expected_wire_bytes=first_status_raw+len(wanted[start]),
        first_status_received_delta=(samples[1]['perf']['received']-samples[0]['perf']['received'])&0xffffffff,
        missing_seq=first+start,missing_wire=wanted[start].hex(' '),missing_payload='[ 16',missing_source='console',
        journal_first=first,journal_last=last,journal_crc=f'{crc:08x}',journal_sha256=sha256(blob).hexdigest(),
        previous_owner_direct_matches=start,current_owner_direct_matches=count-start-1,direct_matches=count-1,
        startup_writes=len(sync),startup_receipts=1,data_frames=len(data),data_bytes=sum(len(p) for _,p,_ in data),
        data_retries=0,commands=commands,readonly_path_mistake_corrected_same_owner=True,
        zero_observed_queue_errors=True,zero_cumulative_perf_error_counts=True,closed=closed,
        limits='The issued six-byte wire frame is absent from raw and the accepted-buffer cumulative delta. This excludes a loss solely after that counter (app read/decoder/display), not EUD/physical USB or early driver refusal. Error observers can clear flags; zero observations do not prove every upstream byte accepted. One startup Ctrl-U still lacks RX acceptance; only startup retries. This measurement is not a fix.')
    return summary,blob

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); args=parser.parse_args()
    summary,blob=analyze(args.root)
    (args.root/'windows-perf-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    (args.root/'windows-tx-journal.bin').write_bytes(blob)
    print(json.dumps({k:summary[k] for k in ('missing_seq','missing_wire','direct_matches','received_delta','raw_bytes','transmitted_delta','perf_samples','startup_writes','startup_receipts','data_frames')}))
