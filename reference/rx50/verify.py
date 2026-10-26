#!/usr/bin/env python3
"""Check RX50 software evidence; no assertion of physical/long-term reliability."""
from hashlib import sha256
import json
from pathlib import Path
import runpy

BASE = Path(__file__).resolve().parent
for line in (BASE / 'SHA256SUMS').read_text().splitlines():
    want, name = line.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == want, name
exports = json.loads((BASE / 'exports.json').read_text())
assert len(exports) == 20
for row in exports:
    got = sha256((BASE / row['name']).read_bytes()).hexdigest()
    assert got == row['exported_sha256'], row['name']
    if Path(row['name']).suffix in ('.raw', '.bin', '.py', '.ps1', '.cs'):
        assert row['byte_identical'] and got == row['original_sha256'], row['name']

analyze = runpy.run_path(str(BASE / 'analyze-window.py'))['analyze']
summary = analyze(BASE)
assert summary == json.loads((BASE / 'windows-window-summary.json').read_text())
assert summary['raw_frames'] == 1508 and summary['raw_bytes'] == 8996
assert summary['native_data_frames'] == 11 and summary['native_data_bytes'] == 101
assert summary['errors_observed'] == 0 and summary['max_in_queue'] == 150
assert summary['max_poll_gap_ms'] == 93 and summary['max_decode_display_ms'] == 39
assert summary['directly_matched_records'] == 287 and summary['unobserved_journal_prefix_records'] == 225
assert summary['journal_crc'] == 'd8df3fa2'
rows = [json.loads(line) for line in (BASE / 'windows-audit.rx-audit.jsonl').read_text().splitlines()]
assert rows[0]['script_sha256'] == sha256((BASE / 'eud-terminal-rx-audit.ps1').read_bytes()).hexdigest()
assert rows[0]['probe_sha256'] == sha256((BASE / 'EudRxAudit.cs').read_bytes()).hexdigest()
runtime = json.loads((BASE / 'installed-managed-runtime.json').read_text())
assert runtime['assembly_sha256'] == rows[0]['assembly_sha256'] == '2b3c17c6208a0b4b6beb94e1a066f99ba06cdb2ea919479e99d47e8c6d96dc71'
assert runtime['ps_version'] == '5.1.26100.9549'
assert runtime['runtime'] == rows[0]['runtime'] == '4.0.30319.42000'
for typ, name in [('System.IO.Ports.SerialStream', 'get_BytesToRead'),
                  ('System.IO.Ports.SerialStream+EventLoopRunner', 'CallEvents')]:
    method, = [r for r in runtime['methods'] if r['type'] == typ and r['name'] == name]
    assert any(call.endswith('UnsafeNativeMethods.ClearCommError') for call in method['calls'])

identity = json.loads((BASE / 'qcusbser-identity.json').read_text())
assert identity['binary_sha256'] == 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
assert identity['pdb_sha256'] == 'ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
assert identity['guid'] == '66581f50-52c9-4a32-9ac6-fe0c57b94a80' and identity['age'] == 1
assert identity['identity_matches'] and identity['section_headers_match']
assert len(identity['unmapped_symbols']) == 3
functions = {r['name']: r for r in identity['functions']}
assert functions['SerialGetCommStatus']['start_rva'] == '0002b11c'
assert functions['SerialGetCommStatus']['code_sha256'] == 'd05d55cf9202978ec39b4267852353bf8683363e76a6ceacf973d254284b48b6'
assert functions['vPutToReadBuffer']['start_rva'] == '00029250'
assert functions['vPutToReadBuffer']['code_sha256'] == 'a63888141fbcd8dde020f40b4dff0b58737aea0e7d470af66efa17e0d0447900'
types = {r['name']: r for r in json.loads((BASE / 'qcusbser-selected-types.json').read_text())}
members = lambda name: {m['name']: m['offset'] for m in types[name]['members']}
ext, status, stats = map(members, ['_DEVICE_EXTENSION', '_SERIAL_STATUS', '_SERIALPERF_STATS'])
assert ext['pSerialStatus'] == 0x2f0 and ext['pPerfstats'] == 0x2e0
assert ext['lReadBufferHigh'] == 0x408 and ext['lReadBufferSize'] == 0x3f8
assert status['Errors'] == 0 and status['AmountInInQueue'] == 8
assert stats['BufferOverrunErrorCount'] == 0x10
# Full disassembly/PDB are local-only. Rerun inspect-qcusbser.py against the
# matched local files to rederive function bytes/identity; never guess a binding.

state = json.loads((BASE / 'final-state.json').read_text())
assert state['serial_closed'] and not state['known_eud_helpers']
assert not any(state[key] for key in ('flash_this_round', 'reboot_this_round', 'new_admin_capture', 'installed_terminal_modified'))
assert state['ports'] == ['COM14'] and len(state['devices']) == 3
assert all(r['Status'] == 'OK' for r in state['devices'])
target, = [r for r in state['target_usbipd'] if '9505' in r]
assert 'Shared' in target and 'Attached' not in target
hashes = {r['Path']: r['Hash'].lower() for r in state['hashes']}
driver = sha256((BASE.parent / 'rx48/eud-journal-candidate.c').read_bytes()).hexdigest()
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c'] == driver == 'e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066'
assert hashes['E:\\eud-host\\eud-terminal.ps1'] == '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\scripts\\eud-terminal.ps1'] == hashes['E:\\eud-host\\eud-terminal.ps1']
assert hashes['E:\\edk2-samurai-out\\logdump-rx48-tx-journal.img'] == '61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d'
print('RX50 evidence verified: current Windows sample normal; old stability faults remain unlocalized.')
