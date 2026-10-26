#!/usr/bin/env python3
"""Export only EUD endpoint control/reset events from the existing RX46 trace."""
from hashlib import sha256
from pathlib import Path
import json
import xml.etree.ElementTree as ET

SOURCE = Path('/mnt/e/edk2-samurai-out/rx46')
DEST = Path(__file__).resolve().parent
NS = {'e': 'http://schemas.microsoft.com/win/2004/08/events/event'}
ET.register_namespace('', NS['e'])
xml = SOURCE / 'etw-r46g-capture.all-local-lr.xml'
events = ET.parse(xml).getroot().findall('e:Event', NS)

def fields(ev):
    return {n.get('Name'): (n.text or '').strip()
            for n in ev.findall('.//e:Data', NS) if n.get('Name')}

def eid(ev):
    return ev.findtext('e:System/e:EventID', namespaces=NS)

def provider(ev):
    return ev.find('e:System/e:Provider', NS).get('Name')

def stamp(ev):
    return ev.find('e:System/e:TimeCreated', NS).get('SystemTime')

rundown = [ev for ev in events if fields(ev).get('fid_idVendor') == '0x5C6'
           and fields(ev).get('fid_idProduct') == '0x9505']
devices = {fields(ev)['fid_UsbDevice'] for ev in rundown}
assert len(devices) == 1
device = next(iter(devices))
target = [ev for ev in events if fields(ev).get('fid_UsbDevice') == device]
controls = [ev for ev in target if provider(ev) == 'Microsoft-Windows-USB-UCX'
            and eid(ev) in ('23', '24')]
resets = [ev for ev in target if provider(ev) == 'Microsoft-Windows-USB-USBHUB3'
          and eid(ev) in ('90', '91', '92', '93')]
selected = ET.Element('Events')
selected.extend([rundown[0], *controls, *resets])
ET.indent(selected)
ET.ElementTree(selected).write(DEST / 'etw-eud-controls.xml', encoding='utf-8',
                              xml_declaration=True)
records = []
for ev in controls:
    records.append({'provider': provider(ev), 'id': int(eid(ev)),
                    'timestamp': stamp(ev), 'fields': fields(ev)})
summary = {
    'source_etl_sha256': sha256((SOURCE / 'etw-r46g-capture.etl').read_bytes()).hexdigest(),
    'source_xml_sha256': sha256(xml.read_bytes()).hexdigest(),
    'vid': '05c6', 'pid': '9505', 'device_handle': device,
    'control_events': records,
    'hub_reset_events': [{'id': int(eid(ev)), 'timestamp': stamp(ev),
                          'fields': fields(ev)} for ev in resets],
    'physical_data_pid_observed': False,
    'payload_bytes_verified': False,
    'note': 'Existing RX46 trace, no new capture. Keep original tracerpt timestamp strings. '
            'CLEAR_FEATURE ENDPOINT_HALT and pipe-reset records are observed; '
            'device data-toggle behavior is a hypothesis, not measured.'
}
(DEST / 'etw-eud-controls.json').write_text(json.dumps(summary, indent=2) + '\n')
print(f'Exported EUD-only controls={len(controls)}, hub events={len(resets)}')
