from pathlib import Path
import base64, json, re, struct, zlib
from hashlib import sha256
root=Path(__file__).resolve().parent
def decode(raw):
    frames=[]; p=0
    while p<len(raw):
        assert raw[p]==0x90 and p+2<=len(raw)
        n=raw[p+1]; assert 1<=n<=4 and p+n+2<=len(raw)
        frames.append(raw[p:p+n+2]); p+=n+2
    return frames,b''.join(f[2:] for f in frames)
owners=[]; allframes=[]
for i in (1,2):
    raw=(root/f'even-owner-{i}.raw').read_bytes()
    frames,body=decode(raw); allframes.append(frames)
    assert body==(root/f'even-owner-{i}.txt').read_bytes()
    events=(root/f'even-owner-{i}.events.txt').read_text(encoding='utf-8-sig')
    sends=[dict(ms=int(ms),n=int(n),payload=payload.strip(),attempt=int(attempt),sync=sync=='True') for ms,n,payload,attempt,sync in re.findall(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)\r?$',events)]
    assert all(s['attempt']==1 for s in sends)
    assert events.count('SYNC fresh Ctrl-U receipt')==1
    audit=[json.loads(t) for t in (root/f'even-owner-{i}.rx-audit.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    assert audit[0]['event']=='opened' and audit[-1]['event']=='closed'
    close=audit[-1]
    assert not any(close[k] for k in ('serial_is_open','pending_input','queued_input','stray','buffered_bytes','retained_pending_perf'))
    assert close['probe_detached'] and close['perf_probe_disposed']
    pos=0
    for a in audit:
        if a['event']=='read': assert a['raw_offset']==pos; pos+=a['returned']
    assert pos==len(raw)==close['audit']['bytes'] and len(frames)==close['received_frames']
    perfs=[a for a in audit if a['event']=='perf']
    for a in perfs:
        p=a['perf']; assert struct.unpack('<6I',bytes.fromhex(p['raw_hex']))==tuple(p[k] for k in ('received','transmitted','frame_errors','serial_overruns','buffer_overruns','parity_errors'))
        assert a['queue']['errors']==a['queue']['flags']==0
    txbytes=sum(2+s['n'] for s in sends)
    assert perfs[-1]['perf']['received']-perfs[0]['perf']['received']==len(raw)
    assert perfs[-1]['perf']['transmitted']-perfs[0]['perf']['transmitted']==txbytes
    initial=[a for a in perfs if a['reason']=='manual-idle'][0]
    owners.append(dict(owner=i,wire_bytes=len(raw),frames=len(frames),frame_parity=len(frames)%2,first_line=body.splitlines()[0].decode(),prefix_present=body.startswith(b'['),sends=sends,closed_ms=close['ms'],received_counter_delta=len(raw),transmitted_counter_delta=txbytes,first_status_bytes=initial['raw_position'],close=close))
one,two=allframes
assert len(one)==74 and len(owners[0]['sends'])==2 and owners[0]['sends'][1]['payload']=='61 62 63'
assert owners[0]['closed_ms']<60000 and owners[1]['closed_ms']<100000
body=decode((root/'even-owner-2.raw').read_bytes())[1].decode()
line,=re.findall(r'(?m)^RVVEVFhKNDg[^\r\n]*',body)
encoded=re.match(r'(?:[A-Za-z0-9+/=]+\r?\n)+',body[body.index(line):])[0]
blob=base64.b64decode(encoded)
magic,ver,size,count,rs,first,last,crc,res=struct.unpack_from('<8sIIIIQQII',blob)
assert (magic,ver,size,count,rs,res,len(blob))==(b'EUDTXJ48',1,3120,512,6,0,3120)
check=bytearray(blob); check[40:44]=bytes(4); assert zlib.crc32(check)==crc and last-first+1==512
wanted=[]
for j in range(512):
    n,source,*data=blob[48+j*6:54+j*6]
    assert 1<=n<=4 and source in (1,2) and not any(data[n:])
    wanted.append(bytes([0x90,n])+bytes(data[:n]))
k,=[j for j in range(493) if wanted[j:j+20]==one[:20]]
prior=decode((root.parent/'rx59/parity-owner-2.raw').read_bytes())[0]
assert prior[-k:]==wanted[:k]
assert one==wanted[k:k+len(one)]
remain=512-k-len(one)
assert two[:remain]==wanted[k+len(one):]
assert re.fullmatch(r'\[\s*\d+\.\d+\] eud: tty byte=15 .*',owners[1]['first_line'])
assert (root/'even-tx-journal.bin').read_bytes()==blob
result=dict(owners=owners,journal=dict(first=first,last=last,crc=f'{crc:08x}',prior_direct_matches=k,first_owner_direct_matches=len(one),second_owner_direct_matches=remain,total_direct_matches=512,missing=[]),even_reversal_prediction_passed=True,first_ctrl_u_accepted_both=True,tx_gap_reproduced=False,physical_data_toggle_measured=False,repair_applied=False,limits=['No driver logging, ETW or initial PnP reload in RX60; joint Arm cancelled before helper start.','Single even reversal, not a stability estimate or final repair.','CPU journal is issue evidence, not physical DATA0/1/ACK.','First-owner data at 30138 ms, later than original aim 22000 ms; manually closed at 38237 ms.'])
assert json.loads((root/'even-summary.json').read_text())==result
print(json.dumps({k:v for k,v in result.items() if k!='owners'},indent=2))
print(json.dumps([{k:o[k] for k in ('owner','wire_bytes','frames','first_line','first_status_bytes','closed_ms')} for o in owners],indent=2))
