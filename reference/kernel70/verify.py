"""Verify saved evidence offline; does not contact or change the phone."""
from pathlib import Path
import base64, gzip, hashlib, json, re, sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
def read(name):
    return (root / name).read_bytes()
report = {'captures': [], 'exports': []}
observed = json.loads(read('windows-close-observations.json'))['captures']
for name, item in observed.items():
    raw, pos, frames, payload = read(name + '.raw'), 0, 0, bytearray()
    while pos < len(raw):
        assert raw[pos] == 0x90 and 1 <= raw[pos + 1] <= 4, (name, pos)
        end = pos + 2 + raw[pos + 1]
        assert end <= len(raw)
        payload.extend(raw[pos + 2:end])
        frames += 1
        pos = end
    assert bytes(payload) == read(name + '.txt'), name
    assert frames == item['frames'] and item['exit_code'] == 0
    assert item['close_observed'] and item['stray'] == item['buffered_bytes'] == 0
    events = read(name + '.events.txt').decode()
    data_frames = [line for line in events.splitlines() if 'TX native' in line and 'sync=False' in line]
    assert len(data_frames) == item['native_data_frames']
    assert all('attempt=1 sync=False' in line and 'len=2 ' not in line for line in data_frames)
    assert b'~ # ' in payload and item['end_marker'].encode() in payload
    report['captures'].append({'name': name, 'frames': frames, 'raw_bytes': len(raw),
        'data_frames_once': len(data_frames), 'startup_retries': item['retries'], 'close_observed': True})

for name, marker, plain_len, gzip_len in [
    ('cmd-db', 'K70C', 5427, 1089), ('provider-state', 'K70S', 907, 344),
    ('latest-dmesg', 'K70L', 85404, 17963), ('runtime-facts', 'K70P', 333, 196),
]:
    text = read(name + '.txt').decode('ascii').replace('\r', '')
    start = re.search(rf'(?m)^{marker}B$', text)
    assert start
    end = re.search(rf'(?m)^{marker}E$', text[start.end():])
    assert end
    lines = text[start.end():start.end() + end.start()].strip().splitlines()
    digest = lines[0].split()[0]
    data = base64.b64decode(''.join(lines[1:]), validate=True)
    assert re.fullmatch('[0-9a-f]{64}', digest) and hashlib.sha256(data).hexdigest() == digest
    body = gzip.decompress(data)
    assert len(data) == gzip_len and len(body) == plain_len
    assert data == read(name + '-received.gz') and body == read(name + '.validated.txt')
    report['exports'].append({'name': name, 'gzip_bytes': len(data), 'plain_bytes': len(body),
        'device_sha256': digest, 'plain_sha256': hashlib.sha256(body).hexdigest(),
        'sha256_pass': True, 'gzip_crc_pass': True})

boot = b'afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\n'
state, facts, cmd = read('provider-state.validated.txt'), read('runtime-facts.validated.txt'), read('cmd-db.validated.txt')
assert all(data.startswith(boot) for data in (state, facts, cmd))
assert b'debugfs' not in state
assert b'ls: /sys/class/i2c-adapter: No such file or directory' in state
assert b'18200000.rsc:regulators-2\n' in facts and b'regulators-2/driver: No such file or directory' in facts
assert b'total 0\nnot attached\n' in facts
log = read('latest-dmesg.validated.txt')
assert log.startswith(b'[    0.000000] Booting Linux') and b'#60 ' in log
assert not any(p in log for p in (b'Kernel panic', b'Oops:', b'mm/ioremap.c:23', b'Voltage update failed freq=2956800'))
assert log.count(b'Attached SCSI disk') == 6 and log.count(b'ret = -95') == 120
audit = json.loads(read('source-audit.json'))
for name, info in audit['sources'].items():
    data = gzip.decompress(read(name + '.source.gz'))
    assert len(data) == info['bytes'] and hashlib.sha256(data).hexdigest() == info['sha256']
assert audit['cmd_db']['entries'] == 139 and audit['cmd_db']['unique_ids'] == 135
assert not audit['cmd_db']['f_resources']
assert not audit['active_mainline_dtb']['supply_consumers'] and not audit['old_android_live_dt']['supply_consumers']
assert len(audit['active_mainline_dtb']['nodes']) == 4
touch = audit['touch_prerequisites']
assert 'CONFIG_I2C_QCOM_GENI=m' in touch['current_config'] and '# CONFIG_RMI4_CORE is not set' in touch['current_config']
assert not touch['native_touch_described']
capacity = json.loads(read('filesystem-capacity.json'))
assert capacity['free_bytes'] == 36737024 and capacity['image_bytes'] == 67108864
preserved = json.loads(read('source-preservation.json'))
for path, digest in preserved.items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
finish = json.loads(read('finish-state.json'))
assert not finish['known_owners'] and not finish['known_linux_owners']
assert len(finish['nodes']) == 3 and all(n['Status'] == 'OK' for n in finish['nodes'])
assert re.search(r'(?m)^6-5\s+05c6:9505\s+[^\r\n]*Shared\s*$', finish['usbipd'])
assert finish['temporary_logging_absent'] and not finish['active_eud_trace'] and not finish['flashed_partitions']
assert not any(finish[k] for k in ('boot_written', 'logdump_written', 'userdata_written', 'gpt_written', 'gadget_binding_attempted', 'eud_control_changes'))
report.update({'linux': {'boot_id': boot.decode().splitlines()[0], 'taint': 0, 'kernel': '#60',
    'dmesg_bytes': len(log), 'scsi_disks': 6, 'panic_or_oops': False},
    'cmd_db': audit['cmd_db'], 'rpmh_unsupported_reads': 120,
    'anomalies': [line for line in log.decode().splitlines() if any(p in line for p in (
        'ldof2', 'failed to acquire drm_bridge', 'unable to determine orientation', 'KASLR disabled', 'tail: write error', 'PC mode'))],
    'limits': ['Complete current saved ring and export, not proof that no older records were overwritten.',
        'No physical PM8009 absence or touchscreen support claim.',
        'Only DT supply references were audited; this is not a schematic/netlist audit.',
        'logdump capacity is from the preserved offline image, not a new phone filesystem scan.',
        'No EUD stability or ordinary USB coexistence validation.']})
if (root / 'SHA256SUMS').exists():
    for line in read('SHA256SUMS').decode().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256(read(name)).hexdigest() == digest, name
print(json.dumps(report, indent=2))
