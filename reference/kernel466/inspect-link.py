"""Constrain S5K3M5SX OP/CSI clocks from fixed OEM source tables.

Pure cached-file analysis. No phone, SDK, compiler, HAL execution or ext4 build
source access. The result is an explicit metadata-derived candidate, not a
datasheet bit-field definition or a measured clock.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel466')
P = PRIVATE.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

old = HERE.parent / 'kernel465'
frozen = json.loads((old / 'frozen-validation.json').read_text())
for row in frozen['public_files']:
    assert sha(old / row['name']) == row['sha256']
assert sha(P / 'kernel465/tele-mode-analysis-private.json') == frozen['private_analysis_sha256']
original = json.loads((P / 'kernel465/tele-mode-analysis-private.json').read_text())

manifest = json.loads((PRIVATE / 'fetched-sources-private.json').read_text())
sources = [dict(**row, bytes=(PRIVATE/'sources'/row['name']).stat().st_size,
                sha256=sha(PRIVATE/'sources'/row['name'])) for row in manifest]
source = PRIVATE / 'sources/oneplus-s5k3m5sxmipiraw_Sensor.c'
text = source.read_text()
clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
assert 'S5K3M5SX_SENSOR_ID' in text and 'write_cmos_sensor(0x0000, 0x30D5)' in text
assert re.search(r'\.mclk\s*=\s*24\b', clean)
assert re.search(r'\.mipi_lane_num\s*=\s*SENSOR_MIPI_4_LANE', clean)
assert re.search(r'\.sensor_output_dataformat\s*=\s*SENSOR_OUTPUT_FORMAT_RAW_Gr', clean)

def braced(text, start):
    begin = text.index('{', start)
    depth = 0
    for index in range(begin, len(text)):
        depth += (text[index] == '{') - (text[index] == '}')
        if depth == 0:
            return text[begin + 1:index]
    raise ValueError('Unterminated input block')

def function(name):
    match = re.search(r'static\s+(?:void|kal_uint32)\s+' + re.escape(name) + r'\([^{}]*\)\s*\{', clean)
    assert match, name
    return braced(clean, match.start())

arrays = {}
for match in re.finditer(r'static kal_uint16 (\w+_setting_array)\[\]\s*=\s*\{', clean):
    values = [int(v, 16) for v in re.findall(r'0x([0-9a-f]+)', braced(clean, match.start()), re.I)]
    assert len(values) % 2 == 0
    arrays[match[1]] = dict(zip(values[::2], values[1::2]))

# Do not generalize the field encoding beyond values0/1 or this matched SX
# selector group. Other Samsung CIS variants have different PLL register maps.
def link_candidate(mclk, registers):
    assert [registers[x] for x in [0x308, 0x30a, 0x30c]] == [8, 1, 0]
    assert registers[0x312] in [0, 1]
    return Fraction(mclk * registers[0x310], registers[0x30e] * (1 if registers[0x312] == 0 else 2))

op_addresses = [0x308, 0x30a, 0x30c, 0x30e, 0x310, 0x312]
oneplus_rows = []
binding = [('pre','preview'),('cap','capture'),('normal_video','normal_video'),
           ('hs_video','hs_video'),('slim_video','slim_video'),
           *[(f'custom{i}',f'custom{i}') for i in range(1,6)]]
feature = clean[clean.index('case SENSOR_FEATURE_GET_MIPI_PIXEL_RATE:'):]
for metadata_name, setting_name in binding:
    m = re.search(r'\.' + metadata_name + r'\s*=\s*\{', clean)
    assert m
    block = braced(clean, m.start())
    metadata = {key: int(value) for key, value in re.findall(r'\.(\w+)\s*=\s*(\d+)', block)}
    registers = arrays[setting_name + '_setting_array']
    setup = function(setting_name + '_setting')
    assert re.search(r'table_write_cmos_sensor\(\s*' + setting_name + r'_setting_array\b', setup)
    scenario_function = 'preview' if metadata_name == 'pre' else 'capture' if metadata_name == 'cap' else setting_name
    scenario = function(scenario_function)
    assert 'imgsensor_info.' + metadata_name + '.pclk' in scenario
    assert re.search(r'\b' + setting_name + r'_setting\(', scenario)
    if metadata_name != 'slim_video':
        assert 'imgsensor_info.' + metadata_name + '.mipi_pixel_rate' in feature
    else:
        assert metadata['mipi_pixel_rate'] == oneplus_rows[0]['mipi_pixel_rate']
    assert [registers[0x34c], registers[0x34e], registers[0x342], registers[0x340]] == [metadata[k] for k in ['grabwindow_width','grabwindow_height','linelength','framelength']]
    link = link_candidate(24000000, registers)
    declared_link = Fraction(metadata['mipi_pixel_rate'] * 10, 2 * 4)
    assert link == declared_link and link.denominator == 1
    oneplus_rows.append(dict(scenario=metadata_name, setup_function=setting_name+'_setting', table=setting_name+'_setting_array',
                             dimensions=[metadata['grabwindow_width'],metadata['grabwindow_height']],
                             mclk_hz=24000000, op_registers={hex(x):registers[x] for x in op_addresses},
                             pclk_metadata=metadata['pclk'], mipi_pixel_rate=metadata['mipi_pixel_rate'],
                             lane_bit_rate=int(link*2), candidate_link_hz=int(link),
                             formula_equals_declared_raw10_four_lane_mipi_rate=True))

# Samsung-authored SX setA provides independent per-lane bit-rate metadata.
# The same repository's setB explicitly says SM and has an older register map;
# it is reviewed as a counterexample and never mixed into this SX calculation.
header = (PRIVATE / 'sources/fimc-is-cis-3m5.h').read_text()
assert re.search(r'#define EXT_CLK_Mhz\s+\(26\)', header)
seta = (PRIVATE / 'sources/fimc-is-cis-3m5-setA.h').read_text()
assert 'S5K3M5SX04_EVT0.0_Ver_0.4_20190429' in seta
seta_clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', seta, flags=re.S)
samsung_rows = []
for match in re.finditer(r'const struct sensor_pll_info_compact sensor_3m5_pllinfo_A_(\w+)\s*=\s*\{', seta_clean):
    name = match[1]
    fields = [x.strip() for x in braced(seta_clean, match.start()).split(',') if x.strip()]
    assert fields[0] == 'EXT_CLK_Mhz * 1000 * 1000' and len(fields) == 5
    declared = int(fields[1], 0)
    table = re.search(r'const u32 sensor_3m5_setfile_A_' + re.escape(name) + r'\[\]\s*=\s*\{', seta_clean)
    assert table
    values = [int(v,16) for v in re.findall(r'0x([0-9a-f]+)', braced(seta_clean, table.start()), re.I)]
    assert len(values) % 3 == 0 and set(values[2::3]) == {2}
    registers = dict(zip(values[::3], values[1::3]))
    assert registers[0x136] == 0x1a00 and registers[0x30c] == 0
    assert registers[0x312] == 0
    link = Fraction(26000000 * registers[0x310], registers[0x30e])
    assert link * 2 == declared
    samsung_rows.append(dict(mode=name, mclk_hz=26000000,
                             partial_op_registers={hex(x):registers[x] for x in op_addresses if x in registers},
                             declared_mipi_lane_bit_rate=declared, candidate_link_hz=int(link),
                             registers_0x0308_0x030a_omitted_not_assumed=True,
                             formula_equals_declared_per_lane_bit_rate=True))
assert len(oneplus_rows) == len(samsung_rows) == 10
setb = (PRIVATE / 'sources/fimc-is-cis-3m5-setB.h').read_text()
assert 'S5K3M5SM_EVT0.1' in setb

target_rows = []
for index in [2, 3]:
    mode = original['modes']['b'][index]
    registers = {int(k):v for k,v in mode['registers'].items()}
    assert registers[0x136] == 0x1333 and registers[0x30e] == 3 and registers[0x310] == 113
    assert all(registers[k] == oneplus_rows[0]['op_registers'][hex(k)] for k in [0x308,0x30a,0x30c])
    link = link_candidate(19200000, registers)
    assert link.denominator == 1
    target_rows.append(dict(mode=index, dimensions=mode['dimensions'], stock_capability=mode['capability'],
                            external_mclk_hz=19200000, op_registers={hex(x):registers[x] for x in op_addresses},
                            candidate_link_hz=int(link), candidate_mipi_lane_bit_rate=int(link*2),
                            candidate_transport_pixel_rate=int(link*2*4/10),
                            output_pixel_clock_metadata_not_used=mode['output_pixel_clock'],
                            metadata_constrained_same_sx_inference=True, measured=False))
assert target_rows[0]['candidate_link_hz'] == 723200000
assert target_rows[1]['candidate_link_hz'] == 361600000
assert len({r['pclk_metadata'] for r in oneplus_rows}) == 1
assert len({r['candidate_link_hz'] for r in oneplus_rows}) >= 3

report = dict(stage=466, sources=sources, source_cache_format='UTF-8 MCP text cache; final newline may be normalized',
              primary_oneplus_source_chip_sx_and_init_id_0x30d5=True,
              same_sx_op_selector_group_matched=['0x0308=8','0x030a=1','0x030c=0'],
              inferred_link_formula='MCLK * reg0x0310 / reg0x030e / (reg0x0312==0 ? 1 : 2)',
              supported_0x0312_values=[0,1], generalized_other_values_or_cis=False,
              oneplus_function_table_metadata_chains=oneplus_rows,
              samsung_sx_seta_declared_bit_rate_crosschecks=samsung_rows,
              older_samsung_sm_setb_and_its_debug_register_names_excluded=True,
              target_candidates=target_rows,
              vt_or_output_pixel_clock_used_to_derive_link=False,
              target_mode2_723p2mhz_candidate_supported=True,
              target_mode3_existing_723p2mhz_metadata_may_overreport_by_two=True,
              target_mode3_formal_driver_or_consumer_plan_changed=False,
              literal_0x0312_datasheet_bitfield_definition_found=False,
              target_pll_physical_clock_measured=False, installable_driver_produced=False,
              frozen465_preserved=True, phone_accessed=False, sdk_bound=False, compiled=False,
              whole_hal_reverse_engineering_expanded=False, coefficients_or_tables_published=False,
              code_sha256=sha(HERE/'inspect-link.py'), passed=True)
(HERE / 'link-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for row in frozen['public_files']:
    assert sha(old/row['name']) == row['sha256']
print(json.dumps(dict(stage=466, oneplus_chains=10, samsung_sx_rate_crosschecks=10, candidates=target_rows, passed=True),indent=2))
