"""Verify frozen RX59 evidence without opening serial/USB or touching configuration."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import base64,gzip,json,re,struct,zlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
def read(name):return (ROOT/name).read_bytes()
def obj(name):return json.loads(read(name))
def zipped(name):return json.loads(gzip.decompress(read(name+'.gz')))
for line in (ROOT/'SHA256SUMS').read_text().splitlines():
    digest,name=line.split('  ',1);assert sha256(read(name)).hexdigest()==digest,name
for name,digest in obj('dependencies.json').items():
    assert sha256((ROOT.parent/name).read_bytes()).hexdigest()==digest,name
for row in obj('exports.json'):
    raw=read(row['name']);assert len(raw)==row['stored_bytes'] and sha256(raw).hexdigest()==row['stored_sha256']
    if row['encoding']=='gzip-mtime-0':
        assert struct.unpack_from('<I',raw,4)[0]==0;raw=gzip.decompress(raw)
    else:assert row['encoding']=='byte-exact'
    assert len(raw)==row['source_bytes'] and sha256(raw).hexdigest()==row['source_sha256']
def decode(raw):
    i=0;fs=[]
    while i<len(raw):
        assert raw[i]==0x90 and i+2<=len(raw)
        n=raw[i+1];assert 1<=n<=4 and i+n+2<=len(raw)
        fs.append(raw[i:i+n+2]);i+=n+2
    return fs
def parse_log(raw):
    i=0;records=[]
    while i<len(raw):
        assert i+13<=len(raw)
        ticks,kind,n=struct.unpack_from('<QBI',raw,i);assert i+13+n<=len(raw)
        records.append((ticks,kind,raw[i+13:i+13+n]));i+=13+n
    return records
captures=[]
for prefix,count in (('first-status',3),('parity',2)):
    for owner in range(1,count+1):
        stem=f'{prefix}-owner-{owner}'
        raw=read(stem+'.raw');fs=decode(raw)
        assert b''.join(x[2:] for x in fs)==read(stem+'.txt')
        audit=[json.loads(s) for s in read(stem+'.rx-audit.jsonl').decode('utf-8-sig').splitlines()]
        assert audit[0]['event']=='opened' and audit[-1]['event']=='closed'
        c=audit[-1];assert len(fs)==c['received_frames'] and len(raw)==c['audit']['bytes']
        assert not any(c[k] for k in ('serial_is_open','pending_input','queued_input','stray','buffered_bytes','retained_pending_perf'))
        assert c['probe_detached'] and c['perf_probe_disposed'] and not c['audit']['error_events']
        pos=0
        for r in audit:
            if r['event']=='read':assert r['raw_offset']==pos;pos+=r['returned']
        assert pos==len(raw)
        perfs=[r for r in audit if r['event']=='perf']
        for r in perfs:
            p=r['perf'];assert p['frame_errors']==p['serial_overruns']==p['buffer_overruns']==p['parity_errors']==0
            assert struct.unpack('<6I',bytes.fromhex(p['raw_hex']))==(p['received'],p['transmitted'],0,0,0,0)
            assert r['queue']['errors']==r['queue']['flags']==0
        assert perfs[-1]['perf']['received']-perfs[0]['perf']['received']==len(raw)
        events=read(stem+'.events.txt').decode('utf-8-sig')
        sends=re.findall(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)\r?$',events)
        assert all(sync=='True' or int(attempt)==1 for ms,n,payload,attempt,sync in sends)
        wire=b''.join(bytes([0x90,int(n)])+bytes.fromhex(payload) for ms,n,payload,attempt,sync in sends)
        assert perfs[-1]['perf']['transmitted']-perfs[0]['perf']['transmitted']==len(wire)
        captures.append(dict(stem=stem,raw=raw,frames=fs,tx=wire,sends=sends,perfs=perfs,close=c))
logs=sorted(ROOT.glob('COM14Rx*.log'));assert len(logs)==5
for cap,log in zip(captures,logs):
    records=parse_log(log.read_bytes());body=b''.join(x[2] for x in records if x[1] in (0,5));assert body==cap['raw']
    cap['log_lengths']=[len(x[2]) for x in records if x[1] in (0,5)]
    tx=log.with_name(log.name.replace('Rx','Tx'))
    assert b''.join(x[2] for x in parse_log(tx.read_bytes()) if x[1] in (1,2,6,7))==cap['tx']
    metadata=zipped(log.name+'.json');assert metadata['sha256']==sha256(log.read_bytes()).hexdigest()
def journal(name):
    raw=read(name);magic,v,size,count,rs,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',raw)
    assert (magic,v,size,count,rs,reserved,len(raw))==(b'EUDTXJ48',1,3120,512,6,0,3120)
    check=bytearray(raw);check[40:44]=bytes(4);assert zlib.crc32(check)==crc and last-first+1==512
    frames=[]
    for i in range(512):
        n,source,*pad=raw[48+6*i:54+6*i];assert 1<=n<=4 and source in (1,2) and not any(pad[n:])
        frames.append(bytes([0x90,n])+bytes(pad[:n]))
    return first,last,crc,frames
first,last,crc,wanted=journal('joint-first-status-tx-journal.bin')
fs=sum([c['frames'] for c in captures[:3]],[])
k,=[i for i in range(492) if wanted[i:i+20]==fs[:20]]
assert k==137 and decode((ROOT.parent/'rx57/windows-log-02.raw').read_bytes())[-k:]==wanted[:k] and fs[:512-k]==wanted[k:]
first,last,crc,wanted=journal('parity-tx-journal.bin')
one,two=captures[3:];k,=[i for i in range(492) if wanted[i:i+20]==one['frames'][:20]]
gap=k+len(one['frames']);assert k==167 and len(one['frames'])==75
assert captures[2]['frames'][-k:]==wanted[:k] and one['frames']==wanted[k:gap] and two['frames'][:512-gap-1]==wanted[gap+1:]
assert first+gap==12407 and wanted[gap]==bytes.fromhex('90 04 5b 31 30 30')
assert len(one['sends'])==2 and [int(x[1]) for x in one['sends']]==[1,4]
assert one['close']['ms']<60000 and two['close']['ms']<100000
assert two['sends'][0][3:] == ('1','True')
initial=next(x for x in two['perfs'] if x['reason']=='manual-idle')
assert initial['raw_position']==330 and initial['perf']['received']-two['perfs'][0]['perf']['received']==330
summary=obj('parity-summary.json');assert summary['journal']['missing']['first_status_cpu_issued_wire_bytes']==336
assert summary['journal']['total_direct_matches']==511
NS={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
for prefix,selected in [('joint-first-status',captures[:3]),('parity',captures[3:])]:
    summary=zipped(prefix+'-etw-summary.json');bound=obj(prefix+'-etw-boundaries.json')
    assert summary['events_lost']==summary['buffers_lost']==0 and bound['failed_positive_in']==0
    evs=ET.fromstring(gzip.decompress(read(prefix+'-etw-eud.xml.gz'))).findall('e:Event',NS)
    rows=[]
    for ev in evs:
        fields={n.get('Name'):(n.text or '').strip() for n in ev.findall('.//e:Data',NS) if n.get('Name')}
        if 'fid_UsbDevice' in fields:assert fields['fid_UsbDevice']==summary['device']
        eid=int(ev.findtext('e:System/e:EventID',namespaces=NS))
        if eid in (26,27):rows.append(dict(id=eid,timestamp=ev.find('e:System/e:TimeCreated',NS).get('SystemTime'),fields=fields))
    assert rows==summary['target_transfers']
    active={};good=[];failed=[];pairs=0
    for row in rows:
        f=row['fields'];key=(f['fid_URB_Ptr'],f['fid_IRP_Ptr'],f['fid_PipeHandle'])
        if row['id']==26:assert key not in active;active[key]=row
        else:
            assert key in active;a=active.pop(key);pairs+=1
            assert int(f['fid_URB_TransferBufferLength'],0)<=int(a['fields']['fid_URB_TransferBufferLength'],0)
            if f['fid_PipeHandle']==summary['pipes']['0x81']:
                if f['fid_IRP_NtStatus']==f['fid_URB_Hdr_Status']=='0x0':good.append(int(f['fid_URB_TransferBufferLength'],0))
                else:failed.append(f)
    assert not active and pairs==bound['pair_count']
    assert good==sum([c['log_lengths'] for c in selected],[]) and sum(good)==sum(len(c['raw']) for c in selected)
    assert len(failed)==bound['failed_in_count'] and all(f['fid_IRP_NtStatus']=='0xC0000120' and f['fid_URB_Hdr_Status']=='0xC0010000' and int(f['fid_URB_TransferBufferLength'],0)==0 for f in failed)
for prefix in ('first-status','parity'):
    status=obj(prefix+'-helper-status.json');assert status['phase']=='restored' and status['etw_stopped'] and status['targeted_original_values_absent'] and not status['failure'] and not status['restore_failure']
for name in ('joint-first-status-post-state.json','parity-post-state.json'):
    state=obj(name);assert state['temporary_values_absent'] and not state['known_owners'] and not state['active_eud_trace']
    assert len(state['nodes'])==3 and all(n['Status']=='OK' for n in state['nodes'])
assert obj('prepared-parity-tests.json')['no_real_registry_or_pnp_or_etw_io']
assert obj('old-rx46-in-summary.json')['failed_positive_length']==0
print('RX59 verified: exact bytes/log/counters; 512 passing and 511+one missing CRC records; target-only ETW all paired; no failed positive IN; restored states.')
