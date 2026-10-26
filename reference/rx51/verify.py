#!/usr/bin/env python3
"""Verify the RX51 failure evidence, without declaring a cause or fix."""
from hashlib import sha256
import json
from pathlib import Path
import runpy

BASE = Path(__file__).resolve().parent
for line in (BASE / 'SHA256SUMS').read_text().splitlines():
    want, name = line.split('  ', 1)
    assert sha256((BASE / name).read_bytes()).hexdigest() == want, name
exports = json.loads((BASE / 'exports.json').read_text())
assert len(exports) == 18
for row in exports:
    got = sha256((BASE / row['name']).read_bytes()).hexdigest()
    assert got == row['exported_sha256'], row['name']
    if Path(row['name']).suffix in ('.raw', '.bin', '.py', '.ps1', '.cs'):
        assert row['byte_identical'] and got == row['original_sha256'], row['name']
analyze = runpy.run_path(str(BASE / 'analyze.py'))['analyze']
result, blob = analyze(BASE)
assert result == json.loads((BASE / 'summary.json').read_text())
assert blob == (BASE / 'tx-journal.bin').read_bytes()
assert result['probe_absent_from_accepted_counts'] and result['shell_variable_empty']
assert result['journal']['direct_matched_frames'] == 511 and result['journal']['missing_seq'] == 11733
assert result['journal']['missing_wire'] == '90 04 5b 20 35 38'
assert (result['marker_ms'], result['probe_ms'], result['end_ms']) == (54079, 54231, 54867)
assert result['failure']['pending_input'] and not result['recovery']['pending_input']
for name, helper in [('console-overlap-01', 'eud-console-overlap.ps1'), ('post-fault-01', 'eud-terminal-rx-audit.ps1')]:
    rows = [json.loads(s) for s in (BASE / (name + '.rx-audit.jsonl')).read_text().splitlines()]
    assert rows[0]['script_sha256'] == sha256((BASE / helper).read_bytes()).hexdigest()
    assert rows[0]['probe_sha256'] == sha256((BASE / 'EudRxAudit.cs').read_bytes()).hexdigest()
    assert rows[0]['assembly_sha256'] == '2b3c17c6208a0b4b6beb94e1a066f99ba06cdb2ea919479e99d47e8c6d96dc71'
    assert rows[-1]['serial_is_open'] is False and rows[-1]['probe_detached']
source = json.loads((BASE / 'source-audit.json').read_text())
assert source['kernel_revision'] == 'e42788eafb0bb9d8dfce319c71ca54c5207b2295'
assert not source['unchanged_core_diff'] and not source['preempt_rt_enabled']
assert 'CONFIG_PREEMPT=y' in source['selected_config'] and 'CONFIG_PRINTK=y' in source['selected_config']
driver = sha256((BASE.parent / 'rx48/eud-journal-candidate.c').read_bytes()).hexdigest()
assert source['sha256']['driver'] == driver == 'e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066'
assert source['sha256']['Image'] == '5565d69447afa60d18aab045030b3ccedb1188daa9022bb379d8a6e38ef9117d'
assert source['init_sha256'] == 'e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab'
state = json.loads((BASE / 'final-state.json').read_text())
assert state['serial_closed'] and not state['known_eud_helpers']
assert not any(state[k] for k in ('flash_this_round', 'reboot_this_round', 'new_admin_capture', 'installed_terminal_modified'))
assert state['ports'] == ['COM14'] and len(state['devices']) == 3
assert all(r['Status'] == 'OK' for r in state['devices'])
assert len(state['target_usbipd']) == 2
assert all('Attached' not in s for s in state['target_usbipd'])
assert any('9505' in s and 'Shared' in s for s in state['target_usbipd'])
hashes = {r['Path']: r['Hash'].lower() for r in state['hashes']}
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c'] == driver
assert hashes['E:\\eud-host\\eud-terminal.ps1'] == hashes['E:\\RealmeX2Pro edk2\\linux-port\\scripts\\eud-terminal.ps1'] == '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert hashes['E:\\edk2-samurai-out\\logdump-rx48-tx-journal.img'] == '61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d'
assert hashes['C:\\Windows\\System32\\drivers\\qcusbser.sys'] == 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
print('RX51 verified: overlap probe absent from RX/tty; one issued console frame missing from Windows raw; cause/fix unproven.')
