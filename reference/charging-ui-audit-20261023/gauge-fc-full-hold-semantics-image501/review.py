"""Only cached primary documents, exact installed-source mappings and retained observations."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
OUT = Path('E:/edk2-samurai-out')
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manual = OUT / 'kernel80/bq28z610-sluua65e.pdf'
manual_text = OUT / 'kernel80/bq28z610-sluua65e.txt'
provenance = read(REF / 'kernel80/source-references.json')
assert sha(manual) == provenance['ti']['sha256'] == 'f62ec12bb5aa23631759e59a378f36d254f9b0e2b5b6b8523a0dd081a13e4139'
assert sha(OUT / 'charging-management-20261023/ti-bq28z610-sluua65.pdf') == sha(manual)
text = manual_text.read_text()
for literal in ['Bit 5: FC', 'BatteryStatus() FLAGS 0x0A/0x0B',
                'two \nconsecutive 40-s periods', 'Fractions of % greater than 99%',
                'The accumulated change in capacity > 0.25 mAh']:
    assert literal in text, literal
gauge_dir = REF / 'charging-oem-audit-20261023/gauge-current-samurai-candidate'
gauge = gauge_dir / 'bq27xxx_battery.c'
baseline = gauge_dir / 'baseline-bq27xxx_battery.c'
assert sha(gauge) == '0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'
assert sha(baseline) == 'b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e'
source = gauge.read_text()
assert '#define BQ27Z561_FLAG_FC\tBIT(5)' in source
assert '[BQ28Z610]  = BQ27XXX_DATA(bq28z610,  0         , BQ27Z561_O_BITS)' in source
table = source.split('bq28z610_regs[BQ27XXX_REG_MAX] = {', 1)[1].split('},', 1)[0]
assert '[BQ27XXX_REG_FLAGS] = 0x0a' in table
full = source[source.index('static bool bq27xxx_battery_is_full'):source.index('/*\n * Return the battery average current', source.index('static bool bq27xxx_battery_is_full'))]
assert full in baseline.read_text() and 'flags & BQ27Z561_FLAG_FC' in full
assert source.index('if (bq27xxx_battery_is_full(di, flags))') < source.index('else if (curr > 0)')

r8 = REF / 'charging-session-20261023/r8-source-integration'
files = read(r8 / 'delivery.json')['files']
charger = r8 / 'kernel-sources/drivers/power/supply/samurai-mp2650.c'
cycle = r8 / 'kernel-sources/drivers/power/supply/oem-full-cycle.h'
for p in [charger, cycle]: assert sha(p) == files[str(p.relative_to(r8)).replace('\\', '/')]
assert 'SM_FULL_NONE, SM_FULL_SOFTWARE, SM_FULL_VOLTAGE, SM_FULL_HARDWARE' in cycle.read_text()
assert 'c->sample_full = (status & 0x0c) == 0x0c;' in charger.read_text()
assert '.hardware_full = c->sample_full' in charger.read_text()
assert 'if (!s->full && in->hardware_full)' in cycle.read_text()
retained = OUT / 'charging-management-20261023/image501-activation/image501-gauge-live-001/after-human-replug-health-01-private/stdout-private.json'
public = REF / 'charging-management-20261023/image501-after-replug-health-result.json'
observed = read(retained)
assert read(public)['raw_sha256'] == sha(retained)
assert observed['passed'] and observed['same_adopted501']
raw = observed['raw']
assert raw['gauge']['capacity'] == '100' and raw['gauge']['status'] == 'Not charging'
assert raw['gauge']['current_now'] == raw['gauge']['current_avg'] == '0'
samples = []
for field in ['telemetry_before', 'telemetry_after']:
    t = {k: int(v, 0) for k, v in (x.split('=', 1) for x in raw[field].split())}
    assert t['flags'] == 192 and t['flags'] & 0x20 == 0
    assert t['full_cause'] == 3 and t['desired_enable'] == 0
    assert all(t[k] == 1 for k in ['logical_full', 'full_holding', 'hold_requested', 'valid', 'protection_ok'])
    assert all(t[k] == 0 for k in ['fault', 'error', 'stop_error', 'latched', 'cycle_timeout', 'gauge_charge_stop'])
    samples.append({k: t[k] for k in ['flags', 'full_cause', 'desired_enable', 'gauge_current_ua',
                                    'cell1_uv', 'cell2_uv', 'age_ms']})
stock = OUT / 'kernel76/stock-oppo_bq27541.c'
stock_audit = read(REF / 'kernel80/charging-source-audit.json')
assert sha(stock) == stock_audit['checked_stock_files']['drivers/power/oppo/gauge_ic/oppo_bq27541.c']['sha256']
assert 'static void bq27541_set_battery_full(bool full)\n{\n\t/* Do nothing */\n}' in stock.read_text()

result = {
    'scope': 'cached BQ BatteryStatus FC mapping and retained healthy Full-hold semantics only',
    'mapping_issue_established': False,
    'gauge_source_sha256': sha(gauge), 'baseline_source_sha256': sha(baseline),
    'BQ28_selected_flags_register': '0x0a word', 'BQ28_selected_FC_mask': '0x0020 bit5',
    'FC_mapping_unchanged_by_Image501': True,
    'generic_BQ27XXX_bit9_not_selected': True, 'GaugingStatus0056_bit1_is_a_different_field': True,
    'TI_manual': {'url': provenance['ti']['url'], 'version': provenance['ti']['version'],
                  'pdf_sha256': sha(manual), 'cached_text_sha256': sha(manual_text),
                  'sections': ['4.6 p26', '4.7 pp26-27', '12.1.6 pp69-70', '13.4.9 p106', '13.6.7 p108']},
    'actual_retained': {'raw_sha256': sha(retained), 'public_receipt_sha256': sha(public),
                        'gauge': raw['gauge'], 'telemetry': samples,
                        'FC_set': False, 'R8_cause3': 'retained MP2650 hardware termination, not gauge FC or software counter'},
    'capacity100_does_not_require_FC': 'RSOCL disabled permits rounded 100 percent; FC set/clear predicates are independently configurable',
    'VCT_required_conditions': ['charging/DSG clear', 'average below configured taper',
                              'max cell plus configured termination window reaches gauge charging target per series cell',
                              'positive accumulated charge above 0.25mAh in each of two consecutive 40-second periods'],
    'conservative_CV_limit': 'lower CV can prevent the configured voltage predicate, but does not necessarily do so; actual termination window and gauge target are unknown',
    'factory2719_limits': ['not proven to be standard 2610 firmware', 'FC/SOCFlagConfig/RSOCL/termination parameters not read',
                           'current FC-clear samples do not validate a physical FC set/clear transition'],
    'R8_sources': {str(p.relative_to(r8)).replace('\\', '/'): sha(p) for p in [charger, cycle]},
    'OEM_stock': {'commit': stock_audit['stock_commit'], 'gauge_sha256': sha(stock),
                  'set_battery_full_is_noop': True, 'generic_bit9_header_not_proof_of_a_used_BQ28_FC_getter': True},
    'recommended_change': 'none from this evidence; preserve truthful Not charging and healthy Full hold, do not infer Full from capacity100 or force Charging',
    'new_I2C_device_network_build_test_Git_operations': False
}
(HERE / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'review_sha256': sha(HERE / 'review.json'), 'mapping_issue_established': False}))
