"""RX57 logging/counter/raw/journal comparison; successful sample is not a repair."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import base64,json,re,runpy,struct,zlib

root=Path(__file__).resolve().parent
decode=runpy.run_path(str(root.parent/'rx55/analyze-windows-perf.py'))['decode']
raw,frames,body=decode(root/'windows-log-02.raw')
assert body.decode('utf-8')==(root/'windows-log-02.txt').read_bytes().decode('utf-8-sig')
audit=[json.loads(s) for s in (root/'windows-log-02.rx-audit.jsonl').read_text().splitlines()]
opened,closed=audit[0],audit[-1]
assert opened['event']=='opened' and closed['event']=='closed'
assert not closed['serial_is_open'] and closed['probe_detached'] and closed['perf_probe_disposed'] and not closed['retained_pending_perf']
assert not closed['stray'] and not closed['buffered_bytes'] and not closed['pending_input'] and not closed['queued_input']
assert closed['received_frames']==len(frames) and closed['audit']['bytes']==len(raw)
assert opened['perf_ioctl']==0x1b008c and opened['overlap_size']==32 and opened['overlap_event_offset']==24 and opened['perf_own_event_low_bit']
for field,name in [('script_sha256','eud-terminal-rx-perf.ps1'),('probe_sha256','EudRxAudit.cs'),('perf_probe_sha256','EudSerialPerf.cs')]:
    dependency=root/name if (root/name).exists() else root.parent/'rx55'/name
    assert opened[field]==sha256(dependency.read_bytes()).hexdigest()
reads=[r for r in audit if r['event']=='read'];offset=0
for r in reads:
    assert r['raw_offset']==offset and r['returned']>0
    offset+=r['returned']
assert offset==len(raw) and len(reads)==closed['audit']['reads']
samples=[r for r in audit if r['event']=='perf']
assert samples[0]['reason']=='opened-before-sync' and samples[-1]['reason']=='before-close'
assert samples[0]['raw_position']==0 and samples[-1]['raw_position']==len(raw)
deltas=[]
for r in samples:
    p=r['perf']; assert p['returned']==24
    assert struct.unpack('<6I',bytes.fromhex(p['raw_hex']))==(p['received'],p['transmitted'],p['frame_errors'],p['serial_overruns'],p['buffer_overruns'],p['parity_errors'])
    assert not any(r['queue'].values()) and not r['buffered_wire'] and not r['pending_input']
for a,b in zip(samples,samples[1:]):
    received=(b['perf']['received']-a['perf']['received'])&0xffffffff
    saved=b['raw_position']-a['raw_position']; assert received==saved
    deltas.append(dict(from_ms=a['ms'],to_ms=b['ms'],received_delta=received,raw_delta=saved))
events=(root/'windows-log-02.events.txt').read_text()
tx=re.findall(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)$',events)
acks=re.findall(r'(?m)^(\d+) ACK native len=(\d+) data=([0-9a-f ]+)$',events)
outs=[];data=[];sync=[]
for ms,n,h,attempt,is_sync in tx:
    payload=bytes.fromhex(h);assert len(payload)==int(n) and int(n)!=2
    outs.append(bytes([0x90,int(n)])+payload)
    (sync if is_sync=='True' else data).append((int(ms),payload,int(attempt)))
assert len(sync)==1 and sync[0][1:]==(b'\x15',1)
assert len(data)==closed['native_frames']==15 and all(attempt==1 for _,_,attempt in data)
assert [bytes.fromhex(h) for _,_,h in acks]==[b'\x15']+[p for _,p,_ in data]
commands=b''.join(p for _,p,_ in data).decode('ascii').splitlines()
assert commands==['dd if=/sys/bus/platform/devices/88e0000.serial/tx_journal of=/tmp/R57J','dd if=/sys/bus/platform/devices/88e0000.serial/tx_journal of=/tmp/R57J bs=4096 count=1','base64 /tmp/R57J']
export,=re.finditer(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',body)
blob=base64.b64decode(re.sub(rb'\s+',b'',export.group()),validate=True)
magic,version,size,count,recsize,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
assert (magic,version,size,count,recsize,reserved)==(b'EUDTXJ48',1,3120,512,6,0) and last-first+1==count
check=bytearray(blob);check[40:44]=bytes(4);assert zlib.crc32(check)==crc
records=[blob[48+6*i:54+6*i] for i in range(count)];wanted=[]
for record in records:
    n,source=record[:2];assert 1<=n<=4 and source in (1,2) and not any(record[2+n:])
    wanted.append(bytes([0x90,n])+record[2:2+n])
align=[k for k in range(count-20) if wanted[k:k+20]==frames[:20]]
assert len(align)==1,align
start=align[0]
assert frames[:count-start]==wanted[start:]
_,previous,_=decode(root.parent/'rx55/windows-perf-01.raw')
assert previous[-start:]==wanted[:start] if start else True
parser=runpy.run_path(str(root/'parse-driver-log.py'))['parse']
log_dir=root/'driver-logs-02' if (root/'driver-logs-02').exists() else root
rx_path,=list(log_dir.glob('*Rx*.log'))
tx_path,=list(log_dir.glob('*Tx*.log'))
rx_log,logged=parser(rx_path);tx_log,_=parser(tx_path)
assert rx_log['complete'] and tx_log['complete'] and logged==raw
nonread=[r for r in rx_log['records'] if r['type'] not in (0,5)]
assert [r['type'] for r in nonread]==[10]+[3]*6+[9]
assert all(r['length']==4 and r['payload_hex']=='200100c0' for r in nonread if r['type']==3)
tx_records=tx_log['records']
logged_out=b''.join(bytes.fromhex(r['payload_hex']) for r in tx_records if r['type'] in (1,2,6,7))
assert logged_out==b''.join(outs)
received=(samples[-1]['perf']['received']-samples[0]['perf']['received'])&0xffffffff
transmitted=(samples[-1]['perf']['transmitted']-samples[0]['perf']['transmitted'])&0xffffffff
assert received==len(raw) and transmitted==len(logged_out)
result=dict(raw_bytes=len(raw),raw_sha256=sha256(raw).hexdigest(),raw_frames=len(frames),read_calls=len(reads),
    opened_ms=opened['ms'],closed_ms=closed['ms'],perf_samples=len(samples),perf_deltas=deltas,received_delta=received,
    transmitted_delta=transmitted,submitted_wire_bytes=sum(map(len,outs)),driver_rx_file_bytes=rx_log['file_bytes'],
    driver_rx_sha256=rx_log['sha256'],driver_rx_records=len(rx_log['records']),driver_rx_type_counts=dict(Counter(r['type'] for r in rx_log['records'])),
    driver_rx_complete=True,driver_rx_equals_raw=True,driver_rx_read_bytes=len(logged),driver_tx_file_bytes=tx_log['file_bytes'],
    driver_rx_nonread_records=nonread,
    driver_tx_records=len(tx_records),driver_tx_type_counts=dict(Counter(r['type'] for r in tx_records)),driver_tx_complete=True,
    driver_tx_equals_submitted=True,journal_first=first,journal_last=last,journal_crc=f'{crc:08x}',journal_sha256=sha256(blob).hexdigest(),
    previous_owner_direct_matches=start,current_owner_direct_matches=count-start,direct_matches=count,
    startup_writes=len(sync),startup_receipts=1,data_frames=len(data),data_bytes=sum(len(p) for _,p,_ in data),data_retries=0,commands=commands,
    corrected_snapshot_read_block_size=True,closed=closed,
    limits='New pre-buffer driver logging is measured and byte-equal to counters/raw in this passing sample. The old startup loss and TX gap were not reproduced; no repair or physical PID/ACK proof. Logger file-write/timing limits remain; file validity alone is not proof of lossless physical observation. Earlier setup failed before COM opening due to a PassThru output-object misclassification, not a new EUD fault.')
if not globals().get('RX57_VERIFY_ONLY',False):
    (root/'capture-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (root/'windows-tx-journal.bin').write_bytes(blob)
    print(json.dumps({k:result[k] for k in ['raw_bytes','raw_frames','driver_rx_records','driver_rx_type_counts','driver_rx_equals_raw','received_delta','transmitted_delta','driver_tx_equals_submitted','journal_first','journal_last','direct_matches','previous_owner_direct_matches','current_owner_direct_matches','startup_writes','data_frames']},indent=2))
