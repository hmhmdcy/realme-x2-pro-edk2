"""Offline association only: observed short-frame parity, not physical DATA0/1."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,re,xml.etree.ElementTree as ET
ROOT=Path('/mnt/e/edk2-samurai-out');DEST=ROOT/'rx59'
REF=Path('/mnt/e/RealmeX2Pro edk2/reference')
def frames(path):
    raw=path.read_bytes();pos=0;count=0
    while pos<len(raw):
        assert raw[pos]==0x90 and pos+2<=len(raw)
        n=raw[pos+1];assert 1<=n<=4 and pos+n+2<=len(raw)
        pos+=n+2;count+=1
    return dict(file=str(path.relative_to(REF)) if path.is_relative_to(REF) else str(path.relative_to(ROOT)),sha256=sha256(raw).hexdigest(),wire_bytes=len(raw),short_frames=count,odd=bool(count%2))
specs=[('RX51','rx51/console-overlap-01.raw',11733),('RX53','rx53/candidate-final-boot.raw',7287),('RX55','rx54/restored-native.raw',7376),('RX46','rx46/etw-r46g-capture.native.raw',None)]
rows=[dict(session=s,preceding=frames(REF/p),next_first_frame_gap_crc_proven=(seq is not None),missing_journal_seq=seq) for s,p,seq in specs]
for i in (1,2):
    rows.append(dict(session='RX58',preceding=frames(ROOT/f'rx58/first-status-owner-{i}.raw'),next_owner=i+1,next_first_frame_gap_crc_proven=False,next_first_status_prefix_present=True))
assert all(x['preceding']['odd'] for x in rows[:4])
assert all(not x['preceding']['odd'] for x in rows[4:])
(DEST/'prior-parity-association.json').write_text(json.dumps(dict(rows=rows,limits=['Three CRC-proven faults and one inferred old prefix fragment are an association, not a failure probability or cause.','RX58 owner 1 passes after a full target PnP reload despite RX57 ending with an odd IN frame count; this is not the same ordinary serial-reopen transition.','Completed short packets are a parity proxy. OUT full packets and subsequent zero-length transfers require separate accounting.','The odd-IN/even-OUT experiment was defined before execution.']),indent=2)+'\n')
NS={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
xml=ROOT/'rx46/etw-r46g-capture.all-local-lr.xml'
evs=ET.parse(xml).getroot().findall('e:Event',NS)
def fields(ev):return {n.get('Name'):(n.text or '').strip() for n in ev.findall('.//e:Data',NS) if n.get('Name')}
def eid(ev):return ev.findtext('e:System/e:EventID',namespaces=NS)
def provider(ev):return ev.find('e:System/e:Provider',NS).get('Name')
device,={fields(ev)['fid_UsbDevice'] for ev in evs if fields(ev).get('fid_idVendor')=='0x5C6' and fields(ev).get('fid_idProduct')=='0x9505'}
target=[ev for ev in evs if fields(ev).get('fid_UsbDevice')==device]
pipe,={fields(ev)['fid_PipeHandle'] for ev in target if provider(ev)=='Microsoft-Windows-USB-UCX' and eid(ev)=='6' and fields(ev).get('fid_bEndpointAddress')=='0x81'}
done=[ev for ev in target if provider(ev)=='Microsoft-Windows-USB-UCX' and eid(ev)=='27' and fields(ev).get('fid_PipeHandle')==pipe]
good=[ev for ev in done if fields(ev).get('fid_IRP_NtStatus')==fields(ev).get('fid_URB_Hdr_Status')=='0x0']
failed=[ev for ev in done if ev not in good]
assert sum(int(fields(ev)['fid_URB_TransferBufferLength'],0) for ev in good)==489
assert all(int(fields(ev)['fid_URB_TransferBufferLength'],0)==0 for ev in failed)
header=next(ev for ev in evs if 'EventsLost' in fields(ev));assert fields(header)['EventsLost']==fields(header)['BuffersLost']=='0'
selected=ET.Element('Events');selected.extend([header,*done]);ET.indent(selected);ET.ElementTree(selected).write(DEST/'old-rx46-in-completions.xml',encoding='utf-8',xml_declaration=True)
(DEST/'old-rx46-in-summary.json').write_text(json.dumps(dict(source_xml_sha256=sha256(xml.read_bytes()).hexdigest(),device=device,in_pipe=pipe,completions=len(done),successful=len(good),successful_bytes=489,successful_lengths=dict(Counter(int(fields(ev)['fid_URB_TransferBufferLength'],0) for ev in good)),failed=[dict(timestamp=ev.find('e:System/e:TimeCreated',NS).get('SystemTime'),fields=fields(ev)) for ev in failed],failed_positive_length=0,events_lost=0,buffers_lost=0,limits=['Old RX46 had no CPU-issued journal. Its prefix fragment does not carry the same proof as RX51/53/55.','This older trace has no positive-length failed IN completion; it does not prove behavior during a later CRC-proven fault.','Preserve original tracerpt timestamps; physical payload bytes, ACKs and DATA0/1 are unmeasured.']),indent=2)+'\n')
print(json.dumps(dict(parity=[(x['session'],x['preceding']['short_frames']) for x in rows],old_success=len(good),old_bytes=489,old_failed=len(failed),old_failed_positive=0),indent=2))
