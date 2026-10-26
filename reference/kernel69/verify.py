"""Offline evidence verification; no USB/serial access and no source mutation."""
from pathlib import Path
import base64, gzip, hashlib, json, re, sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
def read(name):
    return (root / name).read_bytes()

report = {'captures': [], 'exports': [], 'limitations': []}
observations = json.loads(read('windows-close-observations.json'))['captures']
for name, observed in observations.items():
    raw = read(name + '.raw')
    pos = 0
    payload = bytearray()
    frames = 0
    while pos < len(raw):
        assert raw[pos] == 0x90 and 1 <= raw[pos + 1] <= 4, (name, pos)
        end = pos + 2 + raw[pos + 1]
        assert end <= len(raw), (name, pos)
        payload.extend(raw[pos + 2:end])
        frames += 1
        pos = end
    assert bytes(payload) == read(name + '.txt'), name
    assert frames == observed['frames'] and observed['exit_code'] == 0
    events = read(name + '.events.txt').decode()
    data_frames = [line for line in events.splitlines() if 'TX native' in line and 'sync=False' in line]
    assert len(data_frames) == observed['native_data_frames']
    assert all('attempt=1 sync=False' in line for line in data_frames)
    assert all('len=2 ' not in line for line in data_frames)
    assert observed['close_observed'] and observed['stray'] == observed['buffered_bytes'] == 0
    assert b'~ # ' in bytes(payload), name
    report['captures'].append({'name': name, 'raw_bytes': len(raw), 'frames': frames,
                               'data_once': True, 'close_observed': True,
                               'startup_retries': observed['retries']})

for name, marker, plain_bytes, compressed_bytes in [
    ('usb-baseline', 'K69U', 547, 282),
    ('udc-before', 'K69V', 153, 112),
    ('latest-dmesg', 'K69L', 69499, 15676),
    ('driver-facts', 'K69D', 411, 277),
    ('driver-binding', 'K69R', 115, 84),
]:
    text = read(name + '.txt').decode('ascii').replace('\r', '')
    start = re.search(rf'(?m)^{marker}B$', text)
    assert start, name
    end = re.search(rf'(?m)^{marker}E$', text[start.end():])
    assert end, name
    lines = text[start.end():start.end() + end.start()].strip().splitlines()
    digest = lines[0].split()[0]
    assert re.fullmatch('[0-9a-f]{64}', digest)
    data = base64.b64decode(''.join(lines[1:]), validate=True)
    assert hashlib.sha256(data).hexdigest() == digest
    body = gzip.decompress(data)
    assert len(body) == plain_bytes and len(data) == compressed_bytes
    assert data == read(name + '-received.gz') and body == read(name + '.validated.txt')
    report['exports'].append({'name': name, 'compressed_bytes': len(data), 'plain_bytes': len(body),
                              'device_sha256': digest, 'sha256_pass': True, 'gzip_crc_pass': True,
                              'plain_sha256': hashlib.sha256(body).hexdigest()})

facts = read('driver-facts.validated.txt')
assert facts.startswith(b'afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\n')
assert b'Usage: readlink [-fnv] FILE' in facts
bindings = read('driver-binding.validated.txt')
assert bindings == b'a6f8800.usb\n../../../../bus/platform/drivers/dwc3-qcom-legacy\na600000.usb\n../../../../../bus/platform/drivers/dwc3\n'
udc = read('udc-before.validated.txt')
assert b'state:not attached\n' in udc and b'current_speed:UNKNOWN\n' in udc
baseline = read('usb-baseline.validated.txt')
assert b'configfs /sys/kernel/config configfs' in baseline
assert baseline.endswith(b'/sys/kernel/config/usb_gadget:\ntotal 0\n')
log = read('latest-dmesg.validated.txt')
assert log.startswith(b'[    0.000000] Booting Linux')
assert not any(s in log for s in [b'Kernel panic', b'Oops:', b'Voltage update failed freq=2956800', b'mm/ioremap.c:23'])
assert log.count(b'Attached SCSI disk') == 6
report['linux'] = {'boot_id': 'afbbf870-b998-43d8-ab3d-42b3c68c0122', 'taint': 0,
                   'full_saved_dmesg_bytes': len(log), 'scsi_disks': 6, 'panic_or_oops': False,
                   'udc_state': 'not attached', 'gadget_configured': False,
                   'coexistence_verified': False, 'binding': 'dwc3-qcom-legacy'}
report['anomalies'] = [line for line in log.decode().splitlines() if any(p in line for p in (
    'ldof2', 'failed to acquire drm_bridge', 'unable to determine orientation',
    'KASLR disabled', 'tail: write error', 'PC mode', 'ret = -95'))]
report['rpmh_read_unsupported_count'] = log.count(b'ret = -95')
audit = json.loads(read('source-audit.json'))
for name, info in audit['sources'].items():
    data = gzip.decompress(read(name + '.source.gz'))
    assert len(data) == info['bytes'] and hashlib.sha256(data).hexdigest() == info['sha256']
    lines = data.decode().splitlines()
    assert all(lines[item['line'] - 1] == item['text'] for item in info['matches'])
assert audit['findings']['dt_matches_legacy_glue']
assert audit['findings']['legacy_peripheral_sets_vbus_override']
assert not audit['findings']['missing_vbus_forwarding_is_proven_root_cause']
finish = json.loads(read('finish-state.json'))
assert not finish['known_owners'] and not finish['known_linux_owners']
assert len(finish['nodes']) == 3 and all(n['Status'] == 'OK' for n in finish['nodes'])
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$', finish['usbipd'])
assert finish['temporary_logging_absent'] and not finish['active_eud_trace']
assert not finish['flashed_partitions'] and not any(finish[k] for k in (
    'boot_written', 'logdump_written', 'userdata_written', 'gpt_written', 'gadget_binding_attempted', 'eud_control_changes'))
report['limitations'] = [
    'Android EUD/ADB exclusivity is a user observation, not retested here.',
    'Empty gadget and unbound UDC cannot prove an EUD/DWC3 conflict or broken PHY.',
    'Legacy peripheral glue sets VBUS override; missing EUD forwarding alone is not a demonstrated cause.',
    'Saved dmesg is complete in this snapshot and export; logs previously overwritten in the kernel ring would require other evidence.',
    'Captures contain some truncated live prefixes. They are preserved; no missing bytes were filled.',
    'Source snapshots and successful exports are not USB traffic or hardware-coexistence validation.',
]
if (root / 'SHA256SUMS').exists():
    for line in read('SHA256SUMS').decode().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256(read(name)).hexdigest() == digest, name
print(json.dumps(report, indent=2))
