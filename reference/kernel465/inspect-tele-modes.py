"""Read retained S5K3M5 modes and query the retained stock selector.

Offline only. Register sequences and complete selections are saved privately.
No capture transaction, SDK bind, or production source mutation is imported.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel465')
PRIVATE.mkdir(mode=0o700, exist_ok=True)
spec = importlib.util.spec_from_file_location('storage465', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
build = storage.mount.mounted_build()
tree = build.parent / 'source354'
sys.path.insert(0, str(HERE.parent / 'kernel343'))
from mode_tree import ModeTree

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

sources = []
all_modes = {}
for variant in ['a', 'b']:
    path = PRIVATE.parent / f'kernel239/s5k3m5-{variant}-xml-private/Scenario.0/XML/None/sensorDriverData.xml'
    root = ET.parse(path).getroot()
    modes = root.findall('resolutionInfo/resolutionData')
    rows = []
    for index, mode in enumerate(modes):
        sequence = []
        for register in mode.findall('resSettings/regSetting'):
            sequence.append({key: register.findtext(key) for key in ['registerAddr', 'registerData', 'regAddrType', 'regDataType', 'operation', 'delayUs']})
        registers = {int(r['registerAddr']): int(r['registerData']) for r in sequence}
        image = next(stream for stream in mode.findall('streamInfo/streamConfiguration') if stream.findtext('type') == 'IMAGE')
        width = int(image.findtext('frameDimension/width'))
        height = int(image.findtext('frameDimension/height'))
        binning = [int(mode.findtext('horizontalBinning')), int(mode.findtext('verticalBinning'))]
        origin = [registers[0x344] + registers[0x350] * binning[0], registers[0x346] + registers[0x352] * binning[1]]
        rows.append(dict(index=index, dimensions=[width, height], capability=mode.findtext('capability'),
                         declared_frame_rate=float(mode.findtext('frameRate')), lane_count=int(mode.findtext('laneCount')),
                         output_pixel_clock=int(mode.findtext('outputPixelClock')),
                         line_length=int(mode.findtext('lineLengthPixelClock')), frame_length=int(mode.findtext('frameLengthLines')),
                         binning=binning, output_registers_match_declared=[registers[0x34c], registers[0x34e]] == [width, height],
                         analogue_window=[registers[0x344], registers[0x346], registers[0x348] - registers[0x344] + 1, registers[0x34a] - registers[0x346] + 1],
                         reference_origin=origin, registers=registers, sequence=sequence))
    all_modes[variant] = rows
    sources.append(dict(variant=variant, path=str(path.relative_to(PRIVATE.parent)), sha256=sha(path), modes=len(rows)))

active = all_modes['b'][3]
video = all_modes['b'][2]
header = tree / 'drivers/media/i2c/s5k3m5-19mhz-tables.h'
sensor = tree / 'drivers/media/i2c/s5k3m5.c'
text = header.read_text().split('s5k3m5_clock19_mode3_regs[] = {')[1].split('};', 1)[0]
native = [(int(a, 16), int(b, 16)) for a, b in re.findall(r'CCI_REG16\(0x([0-9a-f]+)\),\s*0x([0-9a-f]+)', text, re.I)]
stock = [(int(r['registerAddr']), int(r['registerData'])) for r in active['sequence']]
assert native == stock
assert all(r['operation'] == 'WRITE' and r['regAddrType'] == r['regDataType'] == '2' and r['delayUs'] == '0' for r in video['sequence'])
pll_addresses = [0x136, 0x300, 0x302, 0x304, 0x306, 0x308, 0x30a, 0x30c, 0x30e, 0x310, 0x312]
present_pll = [a for a in pll_addresses if a in active['registers'] or a in video['registers']]
pll_equal = all(active['registers'].get(a) == video['registers'].get(a) for a in present_pll)
different_addresses = sorted(a for a in set(active['registers']) | set(video['registers']) if active['registers'].get(a) != video['registers'].get(a))

binary = PRIVATE.parent / 'kernel306/qtech-s5k3m5sx-tuning-private.bin'
mode_tree = ModeTree(binary)
tags = sorted(set(r['name'] for r in mode_tree.modules.values()))
queries = [(tag, [0, mode, usecase, 0, 0, 0, 0]) for mode in [2, 3] for usecase in [0, 2] for tag in tags]
query_text = ''.join(tag + ' ' + ' '.join(map(str, values)) + '\n' for tag, values in queries)
manager = PRIVATE.parent / 'kernel343/stock-selection-manager'
result = subprocess.run([str(manager), str(binary)], input=query_text, text=True, capture_output=True, timeout=45)
(PRIVATE / 'stock-selection-private.log').write_text(result.stdout + result.stderr)
assert result.returncode == 0, result.stderr
lines = result.stdout.splitlines()
assert len(lines) == len(queries)
selected = []
for serial, ((tag, values), line) in enumerate(zip(queries, lines)):
    expected = mode_tree.select(tag, values)
    assert line.split() == [str(serial), tag, str(expected['uid'] if expected else 0), str(expected['mode_id'] if expected else 0)]
    selected.append(dict(tag=tag, context=values, selection=expected))
by_context = {tuple(r['context']): {} for r in selected}
for row in selected:
    by_context[tuple(row['context'])][row['tag']] = row['selection']
context_comparisons = []
for usecase in [0, 2]:
    a = by_context[(0, 2, usecase, 0, 0, 0, 0)]
    b = by_context[(0, 3, usecase, 0, 0, 0, 0)]
    changed = [tag for tag in tags if a[tag] != b[tag]]
    context_comparisons.append(dict(usecase='Preview' if usecase == 0 else 'Video', compared_tags=len(tags), changed_tags=changed, all_selected_objects_equal=not changed))

private_modes = dict(sources=sources, modes=all_modes, complete_selections=selected,
                     differing_register_addresses=different_addresses,
                     same_pll_addresses=present_pll,
                     binary_sha256=sha(binary), manager_sha256=sha(manager))
(PRIVATE / 'tele-mode-analysis-private.json').write_text(json.dumps(private_modes, indent=2) + '\n')
public_modes = []
for variant, rows in all_modes.items():
    public_modes.append(dict(variant=variant, modes=[{k: v for k, v in row.items() if k not in ['registers', 'sequence']} for row in rows]))
report = dict(stage=465, sources=sources, modes=public_modes,
              current_mode3_table_exactly_matches_retained_b_xml=True,
              current_sensor_source_sha256=sha(sensor), current_header_sha256=sha(header),
              candidate_stock_mode=2, stock_mode2_register_count=len(video['sequence']),
              mode2_mode3_pll_fields_equal=pll_equal, compared_present_pll_field_count=len(present_pll),
              differing_register_address_count=len(different_addresses),
              mode2_timing_frame_rate=video['output_pixel_clock'] / video['line_length'] / video['frame_length'],
              mode2_register_ll_fll_match_declared=video['registers'][0x342] == video['line_length'] and video['registers'][0x340] == video['frame_length'],
              all_module_queries=len(queries), module_tags=len(tags), original_manager_differences=0,
              mode2_mode3_context_comparisons=context_comparisons,
              mode2_preview_video_selected_objects_equal=by_context[(0,2,0,0,0,0,0)] == by_context[(0,2,2,0,0,0,0)],
              tuning_sha256=sha(binary), manager_sha256=sha(manager),
              sensor_mode2_currently_enumerated=False, new_profile_or_driver_built=False,
              phone_accessed=False, sdk_bound=False, hardware_verified=False,
              oem_coefficients_published=False, passed=True)
assert video['dimensions'] == [4208, 2368]
assert video['reference_origin'] == [8, 384]
assert video['binning'] == [1, 1]
assert report['mode2_register_ll_fll_match_declared']
assert all(row['output_registers_match_declared'] for row in all_modes['b'])
(HERE / 'tele-mode-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
