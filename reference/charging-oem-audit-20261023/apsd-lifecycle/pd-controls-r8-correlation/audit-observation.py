"""Correlate the supplied read-only snapshot with pinned OEM bytes; no I/O to a device."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OEM = HERE.parent / 'oem'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((HERE.parent / 'source-manifest.json').read_text())
paths = ['drivers/power/supply/qcom/smb5-reg.h',
         'drivers/power/supply/qcom/qpnp-smb5.c',
         'drivers/power/supply/qcom/smb5-lib.c']
sources = {}
for path in paths:
    p = OEM / path.replace('/', '--')
    expected = next(f for f in manifest['files'] if f['path'] == path)
    assert sha(p) == expected['sha256']
    sources[path] = dict(sha256=sha(p), url=expected['url'])
reg = (OEM / paths[0].replace('/', '--')).read_text()
qpnp = (OEM / paths[1].replace('/', '--')).read_text()
lib = (OEM / paths[2].replace('/', '--')).read_text()
assert re.search(r'#define USBIN_BASE\s+0x1300', reg)
assert re.search(r'#define TYPE_C_CFG_REG\s+\(USBIN_BASE \+ 0x58\)', reg)
for symbol in ['BC1P2_START_ON_CC_BIT', 'APSD_START_ON_CC_BIT']:
    assert re.search(r'#define '+symbol+r'\s+BIT\(7\)', reg)
assert re.search(r'#define BC1P2_SRC_DETECT_BIT\s+BIT\(3\)', reg)

def saved_function(name, text):
    row = next(f for f in manifest['functions'] if f['function'] == name)
    body = '\n'.join(text.splitlines()[row['line']-1:row['end_line']])
    assert hashlib.sha256(body.encode()).hexdigest() == row['sha256']
    return body, row

configure, configure_row = saved_function('smb5_configure_typec', qpnp)
fallback, fallback_row = saved_function('typec_disable_cmd_work', lib)
assert configure.index('smblib_apsd_enable(chg, true);') < configure.index('BC1P2_START_ON_CC_BIT, 0')
assert configure.index('smblib_hvdcp_detect_enable(chg, false);') < configure.index('BC1P2_START_ON_CC_BIT, 0')
assert 'TYPE_C_CFG_REG, APSD_START_ON_CC_BIT, 0' in fallback
snapshot_path = ROOT / 'reference/charging-management-20261023/pd-controls-r8-result.json'
observation = json.loads(snapshot_path.read_text())
assert observation['hardware_writes'] == 0 and len(observation['snapshots']) == 2
assert not observation['pd_contract_inactive_proven']
observed = []
for snapshot in observation['snapshots']:
    registers = snapshot['registers']
    observed.append(dict(start_boottime_ns=snapshot['start_boottime_ns'],
        end_boottime_ns=snapshot['end_boottime_ns'],
        usbin_type_c_cfg=registers['0x1358'],
        start_on_cc_bit=bool(registers['0x1358'] & 0x80),
        source_detection_enabled=bool(registers['0x1362'] & 0x08),
        apsd_status=registers['0x1307'], result=registers['0x1308']))
assert all(s['start_on_cc_bit'] and s['source_detection_enabled'] for s in observed)
provider = ROOT / 'reference/charging-management-20261023/samurai-usb-input.c'
provider_text = provider.read_text()
assert 'regmap_read(' in provider_text and not re.search(r'\bregmap_(?:write|update_bits|bulk_write|raw_write)\s*\(', provider_text)
assert '0x1358' not in provider_text
result = dict(passed=True, scope='local snapshot/source correlation only',
    oem_commit=manifest['commit'], oem_sources=sources,
    actual_oem_functions=[configure_row, fallback_row],
    snapshot_file=str(snapshot_path), snapshot_sha256=sha(snapshot_path),
    observed=observed, provider_sha256=sha(provider),
    conclusions=dict(start_on_cc_clear_postcondition_mismatch=True,
        bc1p2_source_enable_missing=False, current_provider_performs_oem_configure=False,
        historical_initialization_never_occurred_proven=False,
        sdp_classification_caused_by_bit7_proven=False,
        pd_contract_inactive_proven=False, eud_route_causality_proven=False),
    old_function_test_result_sha256=sha(HERE.parent / 'test-result.json'),
    old_suites_repeated=False, phone_accessed=False, hardware_writes=0, sdk_invoked=False)
(HERE / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
