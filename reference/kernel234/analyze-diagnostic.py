"""Publish only protocol metadata and timing, never UART payload/identities."""
from pathlib import Path
import collections
import json
import re

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel234')
native = json.loads((R / 'diagnostic-native-validation.json').read_text())
assert native['exit_code'] == 1 and native['summary']['failed']
assert native['summary']['state'] == 'restored' and not native['summary']['cleanup_errors']
failure = (P / 'native-failure-private.txt').read_text()
assert 'org.bluez.Error.Failed: Not Powered' in failure
log = (P / 'dmesg-candidate-private.txt').read_text()
entries = {}
for line in log.splitlines():
    if 'RXDIAG234 ' not in line:
        continue
    text = line.split('RXDIAG234 ', 1)[1]
    fields = {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', text.split(' head=')[0])}
    seq = fields['seq']
    entry = entries.setdefault(seq, {})
    if 'ns' in fields:
        entry['pre'] = fields
    else:
        entry['post'] = fields
        entry['raw_private'] = bytes.fromhex(text.split(' head=', 1)[1])
trace = (P / 'uart-trace-private.txt').read_text()
events = []
for line in trace.splitlines():
    match = re.search(r'\s(\d+\.\d+): (geni_serial_\w+): (.*)', line)
    if not match:
        continue
    stamp, name, data = match.groups()
    entry = dict(time=float(stamp), name=name, fields=data)
    if 'data=' in data:
        entry['raw'] = bytes.fromhex(data.split('data=', 1)[1].strip())
    events.append(entry)
stats = json.loads((P / 'trace-stats-private.json').read_text())
for text in stats.values():
    for name in ['overrun', 'commit overrun', 'dropped events']:
        assert int(re.search(r'(?m)^' + name + r':\s*(\d+)', text)[1]) == 0
transactions = []
for seq, item in entries.items():
    pre, post, raw = item['pre'], item['post'], item['raw_private']
    assert pre['phase'] == 5 and pre['err'] == 0 and pre['baud'] == 3200000
    assert not pre['had_skb'] and pre['padding'] == 0 and not post['post_skb'] and post['padding'] == 0
    assert len(raw) == pre['count'] == 12
    frames = []
    offset = 0
    while offset < len(raw):
        assert raw[offset] == 4 and offset + 3 <= len(raw)
        length = raw[offset + 2]
        assert offset + 3 + length <= len(raw)
        frames.append(dict(packet_type=4, event_code=raw[offset + 1], payload_bytes=length))
        offset += 3 + length
    timestamp = pre['ns'] / 1e9
    matches = [e for e in events if e['name'] == 'geni_serial_rx_data' and e.get('raw') == raw and abs(e['time'] - timestamp) < .01]
    assert len(matches) == 1
    commands = [e for e in events if e['name'] == 'geni_serial_tx_data' and e.get('raw') == bytes([1, 0x48, 0xfc, 1, 0x11]) and e['time'] < timestamp]
    assert commands
    command = commands[-1]
    clocks = [e for e in events if e['name'] == 'geni_serial_clk_cfg' and command['time'] < e['time'] < timestamp]
    assert clocks
    clock = clocks[-1]['fields']
    values = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', clock)}
    assert values['clk_rate'] == 102400000 and values['clk_div'] == 1
    assert values['desired_rate'] == values['clk_rate']
    termios = [e for e in events if e['name'] == 'geni_serial_set_termios' and command['time'] < e['time'] < timestamp]
    assert termios and 'baud=3200000 ' in termios[-1]['fields']
    mctrl = [e for e in events if e['name'] == 'geni_serial_set_mctrl' and command['time'] < e['time'] < timestamp]
    rfr = [int(re.search(r'uart_manual_rfr=(0x[0-9a-f]+)', e['fields'])[1], 16) for e in mctrl]
    transactions.append(dict(rx_sequence=seq, h4_frames=frames, pre_had_skb=False, pre_len=0,
                             pre_type=0, pre_expect=0, pre_padding=0, post_has_skb=False,
                             parser_error=0, uart_payload_matches_qca_chunk=True,
                             baud_command_payload=17, configured_uart_clock=102400000,
                             configured_clock_divider=1, configured_uart_baud=3200000,
                             configured_baud_not_physical_measurement=True,
                             command_to_rx_ms=round((timestamp - command['time']) * 1000, 3),
                             rfr_writes_between_command_and_rx=rfr))
assert len(transactions) == 2
result = dict(stage=234, actual_phase5_records_correlated=len(transactions),
              event_counts=dict(collections.Counter(e['name'] for e in events)),
              trace_overruns_and_dropped_events=0, transactions=transactions,
              initialization_trace_usable=True, scan_not_completed=True,
              harness_failure='BlueZ Not Powered in the pre-power Adapter1 boolean-property loop; individual failing property was not logged',
              module_and_config_restoration_verified=True, fault_delta=native['summary']['fault_delta'],
              raw_payloads_and_identifiers_retained_private=True,
              no_reassembly_error_reproduced=True, not_proof_of_historical_fix=True,
              printk_may_perturb_timing=True)
(R / 'diagnostic-analysis-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
