"""Prepare a private stock-mode2 table and geometry-only IQ profile draft.

This deliberately does not create a ready-to-install driver or choose CSI rate.
The draft keeps the current provisional control clock and delays explicit.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel465')
spec = importlib.util.spec_from_file_location('storage465', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
storage.mount.mounted_build()
sys.path.append(str(storage.SDK / 'usr/lib/python3.14/site-packages'))
import yaml

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

original = PRIVATE.parent / 'kernel440/factory-s5k3m5-private.yaml'
assert sha(original) == '41cba861b491d583c685e07fdc0e97d635f8922f7132abefa15d0632d4fab0a4'
evidence = json.loads((HERE / 'tele-mode-validation.json').read_text())
assert evidence['passed'] and all(r['all_selected_objects_equal'] for r in evidence['mode2_mode3_context_comparisons'])
analysis = json.loads((PRIVATE / 'tele-mode-analysis-private.json').read_text())
mode = analysis['modes']['b'][2]
assert mode['dimensions'] == [4208, 2368] and mode['capability'] == 'HFR'
base = yaml.safe_load(original.read_text())
assert len(base['modes']) == 1
before = base['modes'][0]
new = copy.deepcopy(before)
new['match'].update(width=4208, height=2368, line_length=4848, frame_length=3312)
new['sensor_controls'].update(width=4208, height=2368, line_length=4848, frame_length=3312)
new['lens_shading'].update(source_span=[2103.0, 1559.0], first_quad=[0.0, 188.0], quad_step=[1.0, 1.0])
assert new['match']['pixel_rate'] == before['match']['pixel_rate'] == 481930000
assert new['sensor_controls']['exposure_delay'] == new['sensor_controls']['gain_delay'] == 2

def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys()
        result = []
        for key in a:
            result.extend(differences(a[key], b[key], f'{path}/{key}'))
        return result
    return [] if a == b else [path]

changed = differences(before, new)
allowed = sorted([f'/{key}/{field}' for key in ['match', 'sensor_controls'] for field in ['width', 'height', 'line_length', 'frame_length']] + ['/lens_shading/first_quad', '/lens_shading/quad_step'])
assert sorted(changed) == allowed
assert new['lens_shading']['core'] == before['lens_shading']['core']
assert new['lens_shading']['golden'] == before['lens_shading']['golden']
assert new['lens_shading']['unit'] == before['lens_shading']['unit']
# Mode0 has the same first active pixel as the current mode3. Crop376 full
# pixels becomes188 Bayer quads, and unbinned mode2 advances one reference quad.
mapping = new['lens_shading']
last = [mapping['first_quad'][i] + (new['match'][['width', 'height'][i]] / 2 - 1) * mapping['quad_step'][i] for i in range(2)]
assert last == [2103.0, 1371.0] and mapping['source_span'][1] - last[1] == 188.0

class NoAlias(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

base['modes'].append(new)
profile = PRIVATE / 'factory-s5k3m5-mode2-draft-private.yaml'
profile.write_text('# Offline draft: stock HFR-labelled mode2; CSI rate and control timing remain unverified.\n' + yaml.dump(base, Dumper=NoAlias, sort_keys=False))
assert yaml.safe_load(profile.read_text())['modes'][0] == before
registers = PRIVATE / 's5k3m5-mode2-draft-regs-private.h'
sequence = mode['sequence']
assert len(sequence) == 53
registers.write_text('/* Private retained stock mode2; no guessed clock or register edits. */\nstatic const struct cci_reg_sequence s5k3m5_clock19_mode2_regs[] = {\n' + ''.join('\t{ CCI_REG16(0x%04x), 0x%04x },\n' % (int(r['registerAddr']), int(r['registerData'])) for r in sequence) + '};\n')
report = dict(stage=465, base_profile_sha256=sha(original), private_profile_sha256=sha(profile),
              private_mode2_table_sha256=sha(registers), stock_mode2_registers_preserved=53,
              prior_mode3_unchanged=True, mode2_stock_capability='HFR',
              mode2_match=new['match'], changed_mode_fields=changed,
              lsc_geometry={key: mapping[key] for key in ['source_span', 'first_quad', 'quad_step']},
              lsc_last_reference_quad=last, stock_lsc_core_golden_and_individual_unit_exactly_reused=True,
              all_other_iq_objects_exactly_reused=True,
              inherited_fixed_camx_mode0_reference_convention=True,
              exact_target_hal_full_resolution_assignment_still_unproven=True,
              control_clock_and_two_frame_delays_are_provisional_from_current_mode3=True,
              linux_link_frequency_selected=False, driver_modified=False, compiled=False,
              installable=False, hardware_verified=False, phone_accessed=False, sdk_bound=False, passed=True)
(HERE / 'mode2-draft-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
