"""Pair retained factory tuning with explicitly selected primary unit data.

All numerical meshes and generated runtime configuration stay private. This is
an explicit diagnostic selection, not automatic OEM illuminant/vendor binding.
"""
from pathlib import Path
import copy, importlib.util, json, math, struct, yaml
import host

HERE = Path(__file__).resolve().parent
P = host.PRIVATE
spec = importlib.util.spec_from_file_location('assembler', HERE.parent / 'kernel322/assemble-profile.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
decoded = json.loads((P.parent / 'kernel326/decoded-unit-private.json').read_text())
profiles = P / 'profiles'
profiles.mkdir(exist_ok=True)
cases = {}
rows = []
f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
for name, model, stage, factory_file, tree_file in [
    ('qtech_s5kgw1', 's5kgw1', 324, 'qtech_s5kgw1', 'qtech_s5kgw1-trees-private.json'),
    ('sunny_s5kgw1', 's5kgw1', 324, 'sunny_s5kgw1', 'sunny_s5kgw1-trees-private.json'),
    ('sunny_imx471', 'imx471', 324, 'sunny_imx471', 'sunny_imx471-trees-private.json'),
    ('qtech_s5k3m5sx', 's5k3m5', 323, 'factory', 'tele-trigger-trees-private.json'),
]:
    roots = json.loads((P.parent / ('kernel' + str(stage)) / tree_file).read_text())
    root = next(r for r in roots if r['uid'] == 25)
    gains, golden = a.assemble(root, 100., 6500., led_index=0)
    primary = next(r for r in decoded[name]['lsc'] if r['illuminant'] == 0)
    unit = dict(zip(a.CHANNELS, primary['channels']))
    assert all(len(v) == 221 and all(math.isfinite(x) and x > 0 for x in v)
               for m in (gains, golden, unit) for v in m.values())
    base = yaml.safe_load((P.parent / ('kernel' + str(stage)) / 'profiles' / (factory_file + '.yaml')).read_text())
    for m in base['modes']:
        assert m['lens_shading']['gains'] == gains
    for kind in ['factory', 'unit']:
        profile = copy.deepcopy(base)
        if kind == 'unit':
            for m in profile['modes']:
                m['lens_shading'].update(golden=copy.deepcopy(golden), unit=copy.deepcopy(unit))
        filename = name + '-' + kind
        text = yaml.safe_dump(profile, sort_keys=False)
        # The installed libcamera YAML reader does not support aliases.
        assert not any(isinstance(event, yaml.AliasEvent) for event in yaml.parse(text))
        (profiles / (filename + '.yaml')).write_text(text)
        for mode in profile['modes']:
            w, h = mode['match']['width'], mode['match']['height']
            tag = '4x3' if h * 4 == w * 3 else '16x9'
            # Telephoto's slightly non-4:3 active size uses the retained 320x240 output.
            output_h = 240 if model == 's5k3m5' or tag == '4x3' else 180
            if model == 's5k3m5': tag = 'full'
            cases[filename + '-' + tag] = dict(model=model, variant=name, kind=kind,
                profile=filename, output='320x' + str(output_h), sensor_size=f'{w}x{h}',
                lsc=True, test_pattern=2 if model == 's5kgw1' else 3)
    factors = [f32(f32(g) / f32(u)) for c in a.CHANNELS for g, u in zip(golden[c], unit[c])]
    rows.append(dict(variant=name, model=model, root_uid=25, modes=len(base['modes']),
        explicit_unit_illuminant=0, primary_values=884, positive_values=True,
        factor_min=min(factors), factor_max=max(factors),
        factor_nonunity_values=sum(v != 1 for v in factors)))
(HERE / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
report = dict(stage=327, profiles=rows, paired_captures=len(cases),
    explicit_factory_lux_index=100., explicit_cct_kelvin=6500., explicit_led_index=0,
    checksum_verified=False, supplier_binding_verified=False,
    tele_illuminant2_descriptor_anomaly_preserved=True, tele_illuminant2_selected=False,
    default_tuning_changed=False, passed=True)
(HERE / 'profile-assembly-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
