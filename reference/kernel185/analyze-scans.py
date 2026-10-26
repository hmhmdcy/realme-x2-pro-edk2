"""Check independent MGMT/HCI traces and preserve cached pairing without publishing IDs."""
from pathlib import Path
import configparser
import json
import re
import struct

root = Path('/var/lib/samurai')
report = {}
for name in ['before-v2', 'after']:
    folder = root / ('k185-scan-' + name)
    result = json.loads((folder / 'result.json').read_text())
    assert result['pass_all'] and result['failure'] is None and not result['monitor_errors']
    assert len(result['rounds']) == 3 and not result['final_powered']
    assert all(r['no_new_pairing_or_connection'] and r['preexisting_pairs_preserved']
               and r['discovery_started'] and r['discovery_stopped'] for r in result['rounds'])
    commands = []
    event_ids = []
    packets = 0
    for line in (folder / 'hci-monitor-private.jsonl').read_text().splitlines():
        raw = bytes.fromhex(json.loads(line)['packet'])
        opcode, index, length = struct.unpack_from('<HHH', raw)
        assert len(raw) == length + 6
        packets += 1
        if opcode == 2:
            assert len(raw) == 9 + raw[8]
            commands.append(struct.unpack_from('<H', raw, 6)[0])
        elif opcode == 3:
            assert len(raw) == 8 + raw[7]
            event_ids.append(raw[6])
    forbidden = {0x0405, 0x0409, 0x040b, 0x040d, 0x0411, 0x042b, 0x042c,
                 0x200d, 0x201a, 0x2043}
    assert not (set(commands) & forbidden)
    assert 0x0401 in commands and (0x200c in commands or 0x2042 in commands)
    assert 0x3e in event_ids
    found_types = {}
    discover = []
    for line in (folder / 'events-mgmt-private.jsonl').read_text().splitlines():
        item = json.loads(line)
        if item['kind'] != 'event':
            continue
        payload = bytes.fromhex(item['payload'])
        if item['event'] == 0x12:
            assert len(payload) == 14 + struct.unpack_from('<H', payload, 12)[0]
            typ = str(payload[6])
            found_types[typ] = found_types.get(typ, 0) + 1
        elif item['event'] == 0x13:
            assert len(payload) == 2
            discover.append(list(payload))
    assert found_types and any(k in found_types for k in ['1', '2'])
    assert len(discover) >= 6 and all(v in [0, 1] for _, v in discover)
    # The kernel can pause/restart inquiry inside one D-Bus discovery session.
    for transport in [1, 6, 7]:
        assert [transport, 1] in discover and [transport, 0] in discover
    oldlog = (folder / 'dmesg-before.txt').read_text()
    newlog = (folder / 'dmesg-after.txt').read_text()
    assert newlog.startswith(oldlog)
    delta = newlog[len(oldlog):]
    faults = {key: delta.count(value) for key, value in {
        'reassembly': 'Frame reassembly failed', 'qca_setup': 'QCA Failed',
        'warning': 'WARNING:', 'oops': 'Oops:', 'gpu': 'gpu fault:',
        'dpu': 'Frame done timeout', 'key_delete': 'failed to remove peer key'}.items()}
    assert not any(v for k, v in faults.items() if k != 'reassembly')
    assert faults['reassembly'] == (1 if name == 'before-v2' else 0)
    health = json.loads((folder / 'health.json').read_text())
    assert len(health) >= 22 and all(h['taint'] == 0 and h['gui_same'] and h['radio_audio_running']
                                   and h['frequency_mhz'] == 5180 for h in health)
    report[name] = {'hci_packets': packets, 'inquiry_and_le_scan_commands_seen': True,
                    'no_connection_or_pairing_commands': True, 'mgmt_found_event_types': found_types,
                    'classic_peer_response_seen': bool(found_types.get('0')),
                    'discovery_start_stop_events': len(discover), 'faults': faults,
                    'health_samples': len(health), 'preexisting_pair_count': result['preexisting_pair_count'],
                    'preexisting_pairs_preserved': True, 'rounds': result['rounds']}
before_keys = json.loads((root / 'k185-policy/pairing-keys-before-private.json').read_text())
current = {}
for p in Path('/var/lib/bluetooth').rglob('info'):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.read(p)
    current[str(p)] = {s: dict(cfg[s]) for s in cfg.sections() if 'key' in s.lower()}
assert all(current.get(p) == keys for p, keys in before_keys.items())
assert all(not keys for p, keys in current.items() if p not in before_keys)
report['preexisting_pairing_keys_unchanged'] = True
report['pulse_rx_nuls'] = int(Path('/sys/kernel/debug/bluetooth/hci0/ibs/pulse_rx_nuls').read_text())
assert report['pulse_rx_nuls'] >= 3
report['transport_fix_passed'] = True
(root / 'k185-load/scan-comparison.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
