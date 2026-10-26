#!/usr/bin/env python3
"""Export reviewed EUD-only ETW headers; keep all-device ETL/XML local."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import xml.etree.ElementTree as ET

SOURCE = Path('/mnt/e/edk2-samurai-out/rx46')
NS = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
ET.register_namespace('', NS['e'])
source_xml = SOURCE / 'etw-r46g-capture.all-local-lr.xml'
events = ET.parse(source_xml).getroot().findall('e:Event', NS)

def fields(ev):
    return {n.get('Name'): (n.text or '').strip()
            for n in ev.findall('.//e:Data', NS) if n.get('Name')}

def event_id(ev):
    return ev.findtext('e:System/e:EventID', namespaces=NS)

def provider(ev):
    return ev.find('e:System/e:Provider', NS).get('Name')

def stamp(ev):
    return ev.find('e:System/e:TimeCreated', NS).get('SystemTime')

rundown = [ev for ev in events if fields(ev).get('fid_idVendor') == '0x5C6'
           and fields(ev).get('fid_idProduct') == '0x9505']
devices = {fields(ev)['fid_UsbDevice'] for ev in rundown}
assert len(devices) == 1, 'Require unique EUD 9505 rundown identity'
device = next(iter(devices))
target = [ev for ev in events if fields(ev).get('fid_UsbDevice') == device]
endpoints = [ev for ev in target if provider(ev) == 'Microsoft-Windows-USB-UCX'
             and event_id(ev) == '6']
pipes = {fields(ev)['fid_bEndpointAddress']: fields(ev)['fid_PipeHandle']
         for ev in endpoints}
assert set(pipes) == {'0x0', '0x2', '0x81'}
out = [ev for ev in target if provider(ev) == 'Microsoft-Windows-USB-UCX'
       and event_id(ev) in ('26', '27')
       and fields(ev).get('fid_PipeHandle') == pipes['0x2']]
assert len(out) == 6
dispatch = [ev for ev in out if event_id(ev) == '26']
complete = [ev for ev in out if event_id(ev) == '27']
assert len(dispatch) == len(complete) == 3
records = []
for start in dispatch:
    a = fields(start)
    matches = [ev for ev in complete if fields(ev)['fid_URB_Ptr'] == a['fid_URB_Ptr']
               and fields(ev)['fid_IRP_Ptr'] == a['fid_IRP_Ptr']]
    assert len(matches) == 1
    stop = matches[0]
    b = fields(stop)
    assert int(a['fid_URB_TransferFlags'], 0) & 1 == 0
    assert a['fid_URB_TransferBufferLength'] == b['fid_URB_TransferBufferLength']
    assert b['fid_URB_Hdr_Status'] == b['fid_IRP_NtStatus'] == '0x0'
    records.append(dict(dispatch=stamp(start), completion=stamp(stop),
                        urb=a['fid_URB_Ptr'], irp=a['fid_IRP_Ptr'],
                        endpoint='0x02', length=int(a['fid_URB_TransferBufferLength'], 0),
                        usbd_status=b['fid_URB_Hdr_Status'], ntstatus=b['fid_IRP_NtStatus']))
assert [r['length'] for r in records] == [12, 3, 3]
header = next(ev for ev in events if 'EventsLost' in fields(ev))
assert int(fields(header)['EventsLost']) == int(fields(header)['BuffersLost']) == 0
# Preserve complete selected Event elements, including nested/repeated Data.
selected = [header, rundown[0]]
for endpoint in ('0x2', '0x81'):
    selected.append(next(ev for ev in endpoints if fields(ev)['fid_bEndpointAddress'] == endpoint))
selected.extend(out)
filtered = ET.Element('Events')
filtered.extend(selected)
ET.indent(filtered)
ET.ElementTree(filtered).write(SOURCE/'etw-eud-selected.xml', encoding='utf-8', xml_declaration=True)
summary = dict(
    source_etl_sha256=sha256((SOURCE/'etw-r46g-capture.etl').read_bytes()).hexdigest(),
    source_xml_sha256=sha256(source_xml.read_bytes()).hexdigest(),
    source_manifest_sha256=sha256((SOURCE/'etw-r46g-capture.manifest.json').read_bytes()).hexdigest(),
    source_all_device_events=len(events),
    provider_event_counts=dict(Counter(provider(ev) or 'ETW-header' for ev in events)),
    events_lost=0, buffers_lost=0, vid='05c6', pid='9505',
    device_handle=device, out_pipe=pipes['0x2'], in_pipe=pipes['0x81'],
    out_transfers=records,
    payload_bytes_verified_by_etw=False,
    note='UCX headers match target endpoint and lengths; original payload bytes and physical USB ACKs are unverified. Preserve tracerpt timestamp strings; do not infer UTC from its unusual offset.')
(SOURCE/'etw-eud-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Reviewed EUD-only export: 3 matched OUT completions, lengths 12/3/3, statuses zero; payload bytes unverified.')
