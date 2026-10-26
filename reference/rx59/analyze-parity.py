"""Offline replay of RX58 joint capture, strict wire/log/CRC/counter checks."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import importlib.util, json, re, struct, zlib
import xml.etree.ElementTree as ET

ROOT=Path('/mnt/e/edk2-samurai-out')
DEST=ROOT/'rx59'
REF=Path('/mnt/e/RealmeX2Pro edk2/reference')
SRC=ROOT/'rx59'
def save(name,value):
    (DEST/name).write_text(json.dumps(value,indent=2)+'\n')
def digest(p): return sha256(p.read_bytes()).hexdigest()
def decode(raw):
    pos=0;frames=[]
    while pos<len(raw):
        assert raw[pos]==0x90 and pos+2<=len(raw)
        n=raw[pos+1];assert 1<=n<=4 and pos+n+2<=len(raw)
        frames.append(raw[pos:pos+n+2]);pos+=n+2
    return frames,b''.join(x[2:] for x in frames)
spec=importlib.util.spec_from_file_location('parser',REF/'rx57/parse-driver-log.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)
reports=[];owners=[]
for i,log in enumerate(sorted((SRC/'driver-logs-parity-01').glob('*Rx*.log')),1):
    report,wire=parser.parse(log);assert report['complete']
    raw=(SRC/f'parity-owner-{i}.raw').read_bytes()
    frames,body=decode(raw)
    assert wire==raw
    assert (SRC/f'parity-owner-{i}.txt').read_bytes()==body
    txlog=log.with_name(log.name.replace('Rx','Tx'))
    txreport,_=parser.parse(txlog);assert txreport['complete']
    txwire=b''.join(bytes.fromhex(x['payload_hex']) for x in txreport['records'] if x['type'] in (1,2,6,7))
    events=(SRC/f'parity-owner-{i}.events.txt').read_text(encoding='utf-8-sig')
    sends=[dict(ms=int(ms),n=int(n),payload=payload.strip(),attempt=int(attempt),sync=sync=='True') for ms,n,payload,attempt,sync in re.findall(r'(?m)^(\d+) TX native len=(\d+) data=([0-9a-f ]+) attempt=(\d+) sync=(True|False)\r?$',events)]
    assert txwire==b''.join(bytes([0x90,x['n']])+bytes.fromhex(x['payload']) for x in sends)
    assert all(x['sync'] or x['attempt']==1 for x in sends)
    audit=[json.loads(x) for x in (SRC/f'parity-owner-{i}.rx-audit.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    assert audit[0]['event']=='opened' and audit[-1]['event']=='closed'
    close=audit[-1]
    assert not any(close[k] for k in ('serial_is_open','pending_input','queued_input','stray','buffered_bytes','retained_pending_perf'))
    assert close['perf_probe_disposed'] and close['probe_detached']
    pos=0
    for x in audit:
        if x['event']=='read': assert x['raw_offset']==pos;pos+=x['returned']
    assert pos==len(raw)==close['audit']['bytes'] and len(frames)==close['received_frames']
    perfs=[x for x in audit if x['event']=='perf']
    for x in perfs:
        assert x['queue']['errors']==x['queue']['flags']==0
        p=x['perf'];assert struct.unpack('<6I',bytes.fromhex(p['raw_hex']))==(p['received'],p['transmitted'],p['frame_errors'],p['serial_overruns'],p['buffer_overruns'],p['parity_errors'])
    assert perfs[-1]['perf']['received']-perfs[0]['perf']['received']==len(raw)
    assert perfs[-1]['perf']['transmitted']-perfs[0]['perf']['transmitted']==len(txwire)
    for rr in (report,txreport):
        rr['source']=Path(rr['source']).name
        save(rr['source']+'.json',rr);reports.append(rr)
    owners.append(dict(owner=i,wire_bytes=len(raw),frames=len(frames),frame_parity=len(frames)%2,prefix_present=body.startswith(b'['),first_line=body.splitlines()[0].decode(),sends=sends,submitted_out_frames=len(sends),successful_read_lengths=dict(Counter(x['length'] for x in report['records'] if x['type'] in (0,5))),nondata_log_records=[x for x in report['records'] if x['type'] not in (0,5)],closed_ms=close['ms'],received_counter_delta=len(raw),transmitted_counter_delta=len(txwire),close=close))
body=decode((SRC/'parity-owner-2.raw').read_bytes())[1].decode()
line,=re.findall(r'(?m)^RVVEVFhKNDg[^\r\n]*',body)
start=body.index(line);tail=body[start:]
import base64
chars=re.match(r'(?:[A-Za-z0-9+/=]+\r?\n)+',tail)[0]
blob=base64.b64decode(chars,validate=False)
magic,ver,size,count,rs,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
assert (magic,ver,size,count,rs,reserved,len(blob))==(b'EUDTXJ48',1,3120,512,6,0,3120)
check=bytearray(blob);check[40:44]=bytes(4);assert zlib.crc32(check)==crc and last-first+1==512
wanted=[]
for j in range(512):
    n,source,*padding=blob[48+j*6:54+j*6]
    assert 1<=n<=4 and source in (1,2) and not any(padding[n:])
    wanted.append(bytes([0x90,n])+bytes(padding[:n]))
frames=sum([decode((SRC/f'parity-owner-{i}.raw').read_bytes())[0] for i in (1,2)],[])
k,=[j for j in range(492) if wanted[j:j+20]==frames[:20]]
prior=decode((ROOT/'rx58/first-status-owner-3.raw').read_bytes())[0]
one=decode((SRC/'parity-owner-1.raw').read_bytes())[0]
two=decode((SRC/'parity-owner-2.raw').read_bytes())[0]
assert len(one)==75 and len(owners[0]['sends'])==2
gap=k+len(one)
assert prior[-k:]==wanted[:k] and one==wanted[k:gap]
assert two[:512-gap-1]==wanted[gap+1:]
assert wanted[gap][:2]==b'\x90\x04' and blob[48+6*gap+1]==2
missing=dict(seq=first+gap,wire_hex=wanted[gap].hex(' '),source='console',first_frame_of_second_owner=True)
assert two[0][2:]+wanted[gap][2:]!=wanted[gap][2:]+two[0][2:]
initial_perf=[x for x in [json.loads(t) for t in (SRC/'parity-owner-2.rx-audit.jsonl').read_text().splitlines()] if x['event']=='perf' and x['reason']=='manual-idle'][0]
status_bytes=initial_perf['raw_position']
assert status_bytes==330
missing['first_status_host_and_counter_bytes']=status_bytes
missing['first_status_cpu_issued_wire_bytes']=status_bytes+len(wanted[gap])
missing['first_status_driver_log_bytes']=sum(x['length'] for x in reports[2]['records'][:len(decode((SRC/'parity-owner-2.raw').read_bytes()[:status_bytes])[0])])
assert missing['first_status_driver_log_bytes']==status_bytes
missing['observed_first_line']=owners[1]['first_line']
missing['issued_first_line']=(wanted[gap][2:]+owners[1]['first_line'].encode()).decode()
assert re.fullmatch(r'\[\s*\d+\.\d+\] eud: tty byte=15 .*',missing['issued_first_line'])
(DEST/'parity-tx-journal.bin').write_bytes(blob)
save('parity-summary.json',dict(owners=owners,journal=dict(first=first,last=last,crc=f'{crc:08x}',prior_direct_matches=k,first_owner_direct_matches=len(one),second_owner_direct_matches=512-gap-1,total_direct_matches=511,missing=missing),driver_payloads_equal_host_raw=True,initial_rx_retry_owner=None,tx_gap_reproduced=True,limits=['Initial full PnP reload differs from ordinary serial reopen.','Both owners manually closed before deadlines.','CPU issue and ETW headers do not reveal physical ACK or DATA0/1.']))

# Preserve EUD-only ETW event elements and all target transfer/control fields.
NS={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
ET.register_namespace('',NS['e'])
xml=SRC/'parity-01.all-local-lr.xml'
evs=ET.parse(xml).getroot().findall('e:Event',NS)
def fields(ev): return {n.get('Name'):(n.text or '').strip() for n in ev.findall('.//e:Data',NS) if n.get('Name')}
def eid(ev): return int(ev.findtext('e:System/e:EventID',namespaces=NS))
def provider(ev): return ev.find('e:System/e:Provider',NS).get('Name')
def stamp(ev): return ev.find('e:System/e:TimeCreated',NS).get('SystemTime')
rundown=[ev for ev in evs if fields(ev).get('fid_idVendor')=='0x5C6' and fields(ev).get('fid_idProduct')=='0x9505']
devices={fields(ev)['fid_UsbDevice'] for ev in rundown};assert len(devices)==1
device=next(iter(devices));target=[ev for ev in evs if fields(ev).get('fid_UsbDevice')==device]
eps=[ev for ev in target if provider(ev)=='Microsoft-Windows-USB-UCX' and eid(ev)==6]
pipes={fields(ev)['fid_bEndpointAddress']:fields(ev)['fid_PipeHandle'] for ev in eps}
assert set(pipes)=={'0x0','0x2','0x81'}
transfers=[ev for ev in target if provider(ev)=='Microsoft-Windows-USB-UCX' and eid(ev) in (26,27)]
controls=[ev for ev in target if provider(ev)=='Microsoft-Windows-USB-UCX' and eid(ev) in (23,24)]
header=next(ev for ev in evs if 'EventsLost' in fields(ev))
assert int(fields(header)['EventsLost'])==int(fields(header)['BuffersLost'])==0
selected=ET.Element('Events');selected.extend([header,*rundown,*eps,*transfers,*controls]);ET.indent(selected)
ET.ElementTree(selected).write(DEST/'parity-etw-eud.xml',encoding='utf-8',xml_declaration=True)
rows=[dict(id=eid(ev),timestamp=stamp(ev),fields=fields(ev)) for ev in transfers]
completed=[r for r in rows if r['id']==27]
ins=[r for r in completed if r['fields']['fid_PipeHandle']==pipes['0x81']]
outs=[r for r in completed if r['fields']['fid_PipeHandle']==pipes['0x2']]
successful=[r for r in ins if r['fields']['fid_IRP_NtStatus']==r['fields']['fid_URB_Hdr_Status']=='0x0']
assert sum(int(r['fields']['fid_URB_TransferBufferLength'],0) for r in successful)==sum(x['wire_bytes'] for x in owners)
nonempty_out=[r for r in outs if int(r['fields']['fid_URB_TransferBufferLength'],0)>0]
assert len(nonempty_out)==12 and sum(int(r['fields']['fid_URB_TransferBufferLength'],0) for r in nonempty_out)==134
assert all(r['fields']['fid_IRP_NtStatus']==r['fields']['fid_URB_Hdr_Status']=='0x0' for r in nonempty_out)
save('parity-etw-summary.json',dict(etl_sha256=digest(SRC/'parity-01.etl'),all_xml_sha256=digest(xml),all_device_events=len(evs),events_lost=0,buffers_lost=0,device=device,pipes=pipes,target_transfers=rows,control_events=[dict(id=eid(ev),timestamp=stamp(ev),fields=fields(ev)) for ev in controls],successful_in_completions=len(successful),successful_in_bytes=8894,in_length_histogram=dict(Counter(int(r['fields']['fid_URB_TransferBufferLength'],0) for r in successful)),failed_in=[r for r in ins if r not in successful],out_completions=len(outs),nonempty_out_completions=len(nonempty_out),out_bytes=134,zero_length_out=[r for r in outs if r not in nonempty_out],payload_bytes_verified_by_etw=False,physical_data_pid_observed=False))
print(json.dumps(dict(missing=missing,owners=[{k:x[k] for k in ('owner','wire_bytes','frames','submitted_out_frames','prefix_present','closed_ms')} for x in owners],journal_first=first,journal_last=last,crc=f'{crc:08x}',prior=k,in_completions=len(successful),in_lengths=dict(Counter(int(r['fields']['fid_URB_TransferBufferLength'],0) for r in successful)),failed_in=len(ins)-len(successful),out_completions=len(outs)),indent=2))
