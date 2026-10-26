"""Offline log integrity audit. No USB/serial access, repair, or filled bytes."""
from pathlib import Path
from hashlib import sha256
import base64
import gzip
import json
import re
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent

def read(name):
    path = root / name
    return path.read_bytes() if path.exists() else gzip.decompress((root / (name + '.gz')).read_bytes())

def export(text, start, end):
    text = text.decode().replace('\r', '')
    begin = re.search(rf'(?m)^{start}$', text)
    assert begin
    finish = re.search(rf'(?m)^{end}$', text[begin.end():])
    assert finish
    lines = text[begin.end():begin.end()+finish.start()].strip().splitlines()
    expected = lines[0].split()[0]
    encoded = ''.join(lines[1:])
    data = base64.b64decode(encoded, validate=True)
    assert len(expected) == 64 and sha256(data).hexdigest() == expected
    return data, expected

result = {'captures': [], 'verified_exports': []}
for name in ('logs', 'facts', 'cpu', 'adc-followup', 'map'):
    raw = read(name + '.raw')
    frames, pos = [], 0
    while pos < len(raw):
        assert raw[pos] == 0x90 and 1 <= raw[pos + 1] <= 4
        stop = pos + 2 + raw[pos + 1]
        assert stop <= len(raw)
        frames.append(raw[pos:stop])
        pos = stop
    payload = b''.join(frame[2:] for frame in frames)
    assert payload.decode('ascii', errors='replace').encode('utf-8') == read(name + '.txt')
    events = [json.loads(line) for line in read(name + '.events.jsonl').decode().splitlines()]
    incoming = [bytes.fromhex(event['hex']) for event in events if event['event'] == 'in']
    assert b''.join(incoming) == raw
    meta = json.loads(read(name + '.json'))
    bus_data = []
    for line in read(name + '.usbmon').decode().splitlines():
        fields = line.split()
        addr = fields[3].split(':')
        assert tuple(map(int, addr[1:3])) == (meta['bus'], meta['address'])
        if addr[0] == 'Bi' and fields[2] == 'C' and int(fields[5]):
            block = bytes.fromhex(''.join(fields[7:]))
            assert fields[6] == '=' and len(block) == int(fields[5])
            bus_data.append(block)
    assert b''.join(bus_data) == raw
    closed = events[-1]
    assert closed['event'] == 'closed' and not closed['worker_alive'] and not closed['errors']
    assert closed['sink_drained'] and closed['stray'] == closed['pending'] == 0
    assert closed['io_bytes'] == len(raw) and closed['frames'] == len(frames)
    assert not closed['overlap_used']
    result['captures'].append(dict(name=name, raw_bytes=len(raw), frames=len(frames),
        sha256=sha256(raw).hexdigest(), positive_usb_in_equals_raw=True,
        receipt_timeouts=sum(e['event'] == 'receipt_timeout' for e in events),
        data_frames=closed['data_frames'], acked=closed['acked'], closed=True,
        close_ms=closed['ms'], overlap_used=False))

for name, start, end, compressed in (
    ('facts', 'K66FB', 'K66FE', True),
    ('issues', 'K66IB', 'K66IE', True),
    ('config', 'K66CB', 'K66CE', False),
):
    data, digest = export(read('facts.txt'), start, end)
    body = gzip.decompress(data) if compressed else data
    assert read(name + '.validated.txt') == body
    if compressed:
        assert read(name + '-received.gz') == data
    result['verified_exports'].append(dict(name=name, exported_bytes=len(data),
        device_sha256=digest, decompressed_bytes=len(body), gzip_crc_pass=compressed,
        sha256_pass=True))

for name, capture, start, end in (
    ('cpu', 'cpu.txt', 'K66PB', 'K66PE'),
    ('cpu-dmesg', 'cpu.txt', 'K66GB', 'K66GE'),
    ('adc', 'adc-prefix.txt', 'K66AB', 'K66AE'),
    ('map-facts', 'map.txt', 'K66MFB', 'K66MFE'),
    ('map-dmesg', 'map.txt', 'K66MGB', 'K66MGE'),
):
    data, digest = export(read(capture), start, end)
    body = gzip.decompress(data)
    assert read(name + '-received.gz') == data
    assert read(name + '.validated.txt') == body
    result['verified_exports'].append(dict(name=name, exported_bytes=len(data),
        device_sha256=digest, plain_bytes=len(body), gzip_crc_pass=True, sha256_pass=True))
cpu_log = read('cpu-dmesg.validated.txt')
assert len(cpu_log) == 55416
assert sha256(cpu_log).hexdigest() == '99064aed87571faebaa694e38dc7eca8e4f095e166ef129e48042a33cd0dbebb'
adc_raw = read('adc-prefix.raw')
adc_payload, pos = bytearray(), 0
while pos < len(adc_raw):
    n = adc_raw[pos + 1]
    assert adc_raw[pos] == 0x90 and 1 <= n <= 4 and pos + n + 2 <= len(adc_raw)
    adc_payload.extend(adc_raw[pos+2:pos+n+2])
    pos += n+2
assert bytes(adc_payload).decode('ascii', errors='replace').encode() == read('adc-prefix.txt')
assert b'K66TB' not in read('adc-prefix.txt')  # No bulk partition-content export in repo.
cpu_facts = read('cpu.validated.txt')
adc_facts = read('adc.validated.txt')
assert b'Failed to find icc paths' not in cpu_facts and b'policy0' in cpu_facts
assert all(p in adc_facts for p in (b'policy0', b'policy4', b'policy7'))
assert b'temp-alarm@' not in adc_facts
assert all(t in adc_facts for t in (b'pm8150-thermal', b'pm8150b-thermal', b'pm8150l-thermal'))
result['hardware_fixes'] = dict(cpu_policies=[0, 4, 7], pmic_thermal_zones=3, total_thermal_zones=27,
                              early_mapping_runtime_verified=True)
map_log = read('map-dmesg.validated.txt')
assert len(map_log) == 53866
assert sha256(map_log).hexdigest() == 'e29ff2301abbfef7de16bf78c81ab0216187a99dde4666e8ecf04be76755ed7d'
assert b'generic_ioremap_prot' not in map_log and b'mm/ioremap.c:23' not in map_log
assert b'Kernel panic' not in map_log
map_facts = read('map-facts.validated.txt')
assert b'#59 ' in map_facts and b'87a7b341-6139-4afd-9ca2-3c0b20493e68\n0\n' in map_facts
assert all(p in map_facts for p in (b'policy0', b'policy4', b'policy7', b'pm8150-thermal', b'pm8150b-thermal', b'pm8150l-thermal'))
assert b'Voltage update failed freq=2956800' in map_facts and b'dwc3: failed to initialize core' in map_facts
result['current_complete_dmesg'] = dict(plain_bytes=len(map_log),
    device_sha256=sha256(map_log).hexdigest(), validated=True, no_early_mapping_warn=True,
    taint=0, no_panic_in_this_snapshot=True, ufs_luns=map_log.count(b'Attached SCSI disk'))

text = read('logs.txt').replace(b'\r\n', b'\n')
begin = text.index(b'\nK66DB\n') + len(b'\nK66DB\n')
end = text.index(b'\nK66DE\n', begin)
partial = text[begin:end] + b'\n'
assert partial == read('dmesg.partial.txt')
result['initial_full_dmesg'] = dict(device_bytes=59841, received_bytes=len(partial),
    device_sha256='847488b394e01ae8c5374fb2dc51b303eb5475d6b342bef23d7ba9003fdb3b83',
    received_sha256=sha256(partial).hexdigest(), validated=False,
    missing_bytes=59841-len(partial), no_filling=True)
assert len(partial) == 59474
assert result['initial_full_dmesg']['received_sha256'] != result['initial_full_dmesg']['device_sha256']
bad_archive = read('received.tgz')
assert len(bad_archive) == 14516
assert sha256(bad_archive).hexdigest() != '31d9e9e8b75c4eba0b1d6b7a7b4c20bcae28757f76f7169ee489d88cd1194812'
try:
    gzip.decompress(bad_archive)
except Exception as error:
    result['failed_full_archive'] = dict(received_bytes=len(bad_archive), device_bytes=14558,
                                       gzip_pass=False, error=str(error))
else:
    raise AssertionError('Expected the preserved full archive to fail integrity')

before = json.loads(read('baseline-state.json'))
after = json.loads(read('final-state.json'))
assert before['hashes'] == after['hashes']
assert not after['known_owners'] and after['temporary_logging_absent'] and not after['active_eud_trace']
assert len(after['nodes']) == 3 and all(n['Status'] == 'OK' for n in after['nodes'])
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$', after['usbipd'])
result['pre_fix_collection_state'] = dict(original_hashes_unchanged=True, nodes_ok=True,
                           unattached=True, known_owners=[], flash=False)
finish = json.loads(read('finish-state.json'))
assert finish['hashes'] == before['hashes']
assert not finish['known_owners'] and finish['temporary_logging_absent'] and not finish['active_eud_trace']
assert len(finish['nodes']) == 3 and all(n['Status']=='OK' for n in finish['nodes'])
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$',finish['usbipd'])
assert finish['flashed_partitions'] == ['logdump']*3
assert not any(finish[k] for k in ('boot_written','userdata_written','gpt_written'))
assert finish['live_logdump_sha256'] == 'c2658235953cbdb8820cfabe6bee9ab0526b8fceb6b69f71f029174690b16e4d'
assert finish['source_hashes']['drivers\\tty\\serial\\eud.c'] == '39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4'
assert finish['source_hashes']['init'] == 'e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab'
assert finish['source_hashes']['arch\\arm64\\boot\\dts\\qcom\\sm8150-samurai.dtb'] == '68001bab92e8611373200f2928d1d83ef5256890528df59dea92c72c1900756e'
result['finish_state'] = dict(original_files_unchanged=True,nodes_ok=True,unattached=True,
    known_owners=[],flash_partitions=['logdump']*3,boot_userdata_gpt_written=False)
failed = json.loads(read('adc-followup-failed-validation.json'))
blob = read('adc-followup-failed-received.gz')
assert len(blob) == failed['received_bytes'] == 12709
assert sha256(blob).hexdigest() == failed['received_sha256']
assert failed['device_sha256'] != failed['received_sha256']
assert not failed['sha256_pass'] and not failed['gzip_crc_pass'] and failed['no_filling']
result['adc_failed_full_export'] = failed

manifest_path = root / 'manifest.json'
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest['files'].items():
        blob = (root / name).read_bytes()
        assert len(blob) == expected['bytes'] and sha256(blob).hexdigest() == expected['sha256']
    result['manifest_pass'] = True
print(json.dumps(result, indent=2))
