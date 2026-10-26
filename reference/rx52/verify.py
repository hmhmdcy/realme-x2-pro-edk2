#!/usr/bin/env python3
"""Verify immutable RX52 captures and the limits of the A/B comparison."""
from hashlib import sha256
import gzip
import json
from pathlib import Path
import runpy

BASE = Path(__file__).resolve().parent
listed = {}
for line in (BASE / 'SHA256SUMS').read_text().splitlines():
    want, name = line.split('  ', 1)
    assert name not in listed and sha256((BASE / name).read_bytes()).hexdigest() == want, name
    listed[name] = want
assert set(listed) == {p.name for p in BASE.iterdir() if p.is_file() and p.name != 'SHA256SUMS'}
exports = json.loads((BASE / 'exports.json').read_text())
assert len(exports) == 19 and len({r['name'] for r in exports}) == 19
for row in exports:
    data = (BASE / row['name']).read_bytes()
    got = sha256(data).hexdigest()
    assert got == row['exported_sha256'], row['name']
    if row['name'].endswith('.gz'):
        assert sha256(gzip.decompress(data)).hexdigest() == row['original_sha256']
    elif Path(row['name']).suffix in ('.raw', '.bin', '.py'):
        assert row['byte_identical'] and got == row['original_sha256'], row['name']
    else:
        assert not data.startswith(b'\xef\xbb\xbf') and b'\r\n' not in data, row['name']
analyze = runpy.run_path(str(BASE / 'analyze.py'))['analyze']
saved = json.loads((BASE / 'summary.json').read_text())
for index, (name, helper, expected) in enumerate([
    ('usb-overlap-01', 'eud-usb-overlap.py', (13220, 2220, 982, 510, 8423, 9356)),
    ('usb-overlap-02', 'eud-usb-overlap-pipelined.py', (13245, 2225, 990, 512, 854, 4075)),
]):
    result, blob = analyze(BASE, name)
    assert result == saved[index] and blob == (BASE / (name+'-journal.bin')).read_bytes()
    actual = (result['raw_bytes'], result['raw_frames'], result['console_zero_digits'],
              result['journal']['observed_frames'], result['max_body_in_requeue_gap']['us'],
              result['in_statuses']['-2'])
    assert actual == expected and result['in_statuses']['0'] == result['raw_frames']
    assert set(result['in_statuses']) == {'0', '-2'}
    meta = json.loads((BASE / (name+'.json')).read_text())
    assert meta['helper_sha256'] == sha256((BASE / helper).read_bytes()).hexdigest()
    assert meta['pyusb_version'] == '1.2.1-2' and meta['overlap_delay_ms'] == 152
    assert meta['libusb_backend_sha256'] == '0c86fc30235ce1d762ae14721e19a5efcadd8eea7d94771d4767d9b099ffba60'
    assert not meta['automatic_data_retries'] and meta['hold_overlap_timeout_for_manual_sync']
    assert meta['endpoints'] == [dict(address=129, attributes=2, max_packet=16), dict(address=2, attributes=2, max_packet=16)]
    assert result['probe_absent_from_rx_tty'] and result['shell_variable_empty']
    assert result['added_empty_irq'] == 1 and result['full_in_equals_raw']
    assert result['no_control_transfers_in_capture'] and result['probe_submissions'] == 1
assert saved[0]['journal']['gap_position_ambiguous'] and not saved[1]['journal']['gap_position_ambiguous']
assert saved[1]['closed']['sink_drained'] and saved[1]['closed']['max_sink_queue'] == 2
epoch = json.loads((BASE / 'source-epoch.json').read_text())
old = json.loads((BASE.parent / 'rx51/source-audit.json').read_text())
driver = sha256((BASE.parent / 'rx48/eud-journal-candidate.c').read_bytes()).hexdigest()
assert epoch['kernel_revision'] == old['kernel_revision'] and not epoch['preempt_rt_enabled']
for name in ('driver', 'Image', 'DTB', 'config'):
    assert epoch['sha256'][name] == old['sha256'][name]
assert epoch['sha256']['driver'] == driver == 'e25d7fe215cab2ff842bdc3aa3bdf644d8f1701ecd27ea694fe43f848f5f5066'
assert epoch['sha256']['init'] == old['init_sha256']
assert epoch['sha256']['busybox'] == '999cb969d09093a71716cfc747bb53cdada3f332c05eb5046c56e0f66a4d6d22'
state = json.loads((BASE / 'final-state.json').read_text())
assert state['serial_closed'] and state['usb_owners_closed_and_detached'] and not state['known_eud_helpers']
assert not any(state[k] for k in ('flash_this_round', 'reboot_this_round', 'new_admin_capture', 'installed_terminal_modified'))
assert state['wsl_root_usbmon'] and state['ports'] == ['COM14'] and len(state['devices']) == 3
assert all(r['Status'] == 'OK' for r in state['devices'])
assert len(state['target_usbipd']) == 2 and not any('Attached' in s for s in state['target_usbipd'])
assert any('9505' in s and 'Shared' in s for s in state['target_usbipd'])
hashes = {r['Path']: r['Hash'].lower() for r in state['hashes']}
assert hashes['E:\\RealmeX2Pro edk2\\linux-port\\eud.c'] == driver
assert hashes['E:\\eud-host\\eud-terminal.ps1'] == hashes['E:\\RealmeX2Pro edk2\\linux-port\\scripts\\eud-terminal.ps1'] == '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert hashes['E:\\edk2-samurai-out\\logdump-rx48-tx-journal.img'] == '61c0315cd24e24ce2bd020a8179647862eeacced28b142f21ffa0d2de00b953d'
assert hashes['C:\\Windows\\System32\\drivers\\qcusbser.sys'] == 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
print('RX52 verified: same-owner RX probe absent in both paths; 510/512 then 512/512 TX matches; continuous IN reduces requeue gap in one contrast, no general fix claimed.')
