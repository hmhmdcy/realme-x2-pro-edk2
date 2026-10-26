"""Offline checks for RX58 association, exact branches and unexecuted plan."""
from hashlib import sha256
import json
from pathlib import Path
import re
import runpy

root = Path(__file__).resolve().parent
for line in (root/'SHA256SUMS').read_text().splitlines():
    checksum, name = line.split('  ', 1)
    assert sha256((root/name).read_bytes()).hexdigest() == checksum, name
ref = root.parent
result = runpy.run_path(str(root/'analyze-cross-samples.py'))['analyze'](ref)
assert result == json.loads((root/'cross-sample-summary.json').read_text())
assert [r['first_sync_attempts'][-1]['attempt'] for r in result['gaps']] == [2, 1, 2]
assert all(r['direct_matches'] == 511 for r in result['gaps'])
driver = json.loads((root/'driver-boundary-summary.json').read_text())
assert driver['binary_sha256'] == 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
assert driver['pdb_sha256'] == 'ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
assert driver['guid'] == '66581f50-52c9-4a32-9ac6-fe0c57b94a80' and driver['age'] == 1
expected = {
    'StartTheReadGoing': '39d3fc6c38cc37d3b1adb8bd25b53fd9261172448b56e3957e20f0c53f7fc944',
    'ReadIrpCompletion': '045b377972566306ab84843da2295e3c19acbb94a76d61a000315e97efc12f4a',
    'QCMRD_L1MultiReadThread': 'eeda3e9b1ba2e303274629c5e71b19a67b30b751e20016cf09c2865aa076ac37',
    'QCMRD_L2MultiReadThread': '6d881629076f62148ae1b76693e1c81f6675c8ab5b72efdb8c27c8a94f0b8f90',
    'MultiReadCompletionRoutine': '16580ec32052959093f50a0c2929d48365d99975cdf6c0ab72cc2adaf107a41a',
}
assert {f['name']:f['code_sha256'] for f in driver['functions']} == expected
for row in driver['excerpts']:
    lines = (root/row['filename']).read_text().splitlines()
    code = bytearray()
    pos = int(row['begin'], 16)
    for line in lines:
        address = int(line[:8], 16)
        match = re.match(r'[0-9a-f]{8} ((?:[0-9a-f]{2} )+)', line)
        assert match and address == pos
        blob = bytes.fromhex(match[1])
        code.extend(blob); pos += len(blob)
    assert pos == int(row['end'], 16) and len(code) == row['bytes']
    assert sha256(code).hexdigest() == row['excerpt_code_sha256']
    assert row['function_code_sha256'] == expected[row['name']]
refs = json.loads((root/'callback-refs.json').read_text())
assert len(refs) == 1 and refs[0]['caller'] == 'StartTheReadGoing'
assert refs[0]['code_sha256'] == expected['StartTheReadGoing']
assert refs[0]['rva'] == '00028467'
assert any(r['rva'] == '0002846e' and r['bytes'] == '48 89 47 60' for r in refs[0]['instructions'])
assert 0x28467+7-0x3066 == 0x25408
mock = json.loads((root/'prepared-measurement-tests.json').read_text())
assert mock['parser_clean'] and mock['no_real_registry_or_pnp_or_etw_io'] and mock['no_serial_opened']
assert mock['admin_helper_sha256'] == sha256((root/'driver-log-etw-admin.ps1').read_bytes()).hexdigest()
assert len(mock['cases']) == 7 and [r['calls'] for r in mock['bounded_stop_cases']] == [1, 2, 3]
plan = json.loads((root/'measurement-plan-01.json').read_text())
assert plan['mode'] == 'Plan' and not plan['admin'] and not any(v['present'] for v in plan['original'])
assert plan['target_reload_count'] == 2 and plan['serial_owner_count'] == 3 and plan['capture_deadline_seconds'] == 180
state = json.loads((root/'readonly-state.json').read_text())
assert len(state['nodes']) == 3 and all(r['Status'] == 'OK' for r in state['nodes'])
assert not state['known_owners'] and state['temporary_values_absent']
assert not state['new_control_exists'] and not state['new_log_directory_exists'] and not state['new_etl_exists']
assert re.search(r'^6-5\s+05c6:9505\s+.*Shared\s*$', state['usbipd'], re.M) and 'Attached' not in state['usbipd']
assert state['hashes']['C:\\Windows\\System32\\drivers\\qcusbser.sys'] == driver['binary_sha256']
assert state['hashes']['E:\\eud-host\\eud-terminal.ps1'] == '9c7a16f1f389a0dbbf3436f1383221cdf6c00e348f25b6e3590a479dab103d57'
assert state['hashes']['E:\\edk2-samurai-out\\logdump-rx53-console-rx.img'] == '50f951a4093dab3e4b93339a998b06583a01b75cd3c8cb39f67ca70e84fc5a93'
print('RX58 verified: three first-frame associations, exact completion/logger gates, restored read-only baseline and prepared unexecuted measurement.')
