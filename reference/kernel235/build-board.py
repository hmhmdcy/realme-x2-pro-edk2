"""Compile the additive lab board with the real recipe, check all semantic deltas."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import shlex
import shutil
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
K = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = P / 'board-build-r2'
out.mkdir(mode=0o700)
spec = importlib.util.spec_from_file_location('fdt', R.parent / 'kernel211/fdt_compare.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
parse = f.parser()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old_dtb = P.parent / 'kernel232/board-build/experimental-p-identity-only.dtb'
assert sha(old_dtb) == '7e8345aea103e60d1d8016c8245832a169b4630ab54f662274e8e546dd8d9ae3'
old = parse(old_dtb.read_bytes())
old_source = R.parent / 'kernel232/experimental-p-identity-only.dts'
assert sha(old_source) == json.loads((R.parent / 'kernel232/board-source-validation.json').read_text())['source_hashes'][old_source.name]
source = out / 'imx319-p-lab.dts'
source.write_text(old_source.read_text() + '\n#include "imx319-p-lab.dtsi"\n')
shutil.copyfile(R / 'imx319-p-lab.dtsi', out / 'imx319-p-lab.dtsi')
recipe = (K / 'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=', 1)[1]
commands, current = [], []
for token in shlex.split(recipe):
    if token == ';':
        commands.append(current)
        current = []
    else:
        current.append(token)
commands.append(current)
assert len(commands) == 3
base = 'arch/arm64/boot/dts/qcom/'
mapping = {base + 'sm8150-samurai.dts': str(source),
           base + '.sm8150-samurai.dtb.d.pre.tmp': str(out / 'pre.d'),
           base + '.sm8150-samurai.dtb.d.dtc.tmp': str(out / 'dtc.d'),
           base + '.sm8150-samurai.dtb.dts.tmp': str(out / 'imx319-p-lab.pp.dts'),
           base + 'sm8150-samurai.dtb': str(out / 'imx319-p-lab.dtb')}
def rewrite(arg):
    for a, b in sorted(mapping.items(), key=lambda pair: -len(pair[0])):
        arg = arg.replace(a, b)
    return arg
for index, args in enumerate(commands[:2]):
    args = [rewrite(arg) for arg in args]
    if index == 0:
        args += ['-iquote', str(K / base)]
    run = subprocess.run(args, cwd=K, capture_output=True, timeout=60)
    (out / (str(index) + '-private.log')).write_bytes(run.stdout + run.stderr)
    assert run.returncode == 0, run.stderr[-2000:]
yaml = out / 'imx319-p-lab.yaml'
run = subprocess.run(['dtc', '-O', 'yaml', '-o', str(yaml), str(out / 'imx319-p-lab.pp.dts')], capture_output=True, timeout=60)
(out / 'yaml-private.log').write_bytes(run.stdout + run.stderr)
assert run.returncode == 0, run.stderr[-1500:]
dtb = out / 'imx319-p-lab.dtb'
new = parse(dtb.read_bytes())
semantic = f.compare(old, new, yaml)
(out / 'semantic-private.json').write_text(json.dumps(semantic, indent=2) + '\n')
cells = lambda b: [int.from_bytes(b[i:i+4], 'big') for i in range(0, len(b), 4)]
handle = lambda path: cells(new[path]['phandle'])[0]
def one(predicate):
    paths = [path for path in new if predicate(path)]
    assert len(paths) == 1, paths
    return paths[0]
q = one(lambda path: path.endswith('/pmic@4') and 'qcom,initial-address' in new[path])
p = q.rsplit('/', 1)[0] + '/pmic@8'
sensor = one(lambda path: new[path].get('compatible') == b'realme,rmx1931-imx319\0')
bus = sensor.rsplit('/', 1)[0]
cci = bus.rsplit('/', 1)[0]
assert cci.endswith('/cci@ac4a000') and bus.endswith('/i2c-bus@1'), (cci, bus)
camss = one(lambda path: b'qcom,sm8150-camss\0' in new[path].get('compatible', b''))
rx = camss + '/ports/port@1/endpoint'
tx = sensor + '/port/endpoint'
tlmm = one(lambda path: b'qcom,sm8150-pinctrl\0' in new[path].get('compatible', b''))
camcc = one(lambda path: b'qcom,sm8150-camcc\0' in new[path].get('compatible', b''))
front = one(lambda path: new[path].get('compatible') == b'sony,imx471\0')
vif = one(lambda path: 'phandle' in new[path] and cells(new[front]['vif-supply']) == [handle(path)])
assert cells(new[vif]['regulator-min-microvolt']) == cells(new[vif]['regulator-max-microvolt']) == [1800000]
constants = {}
for line in (K / 'include/dt-bindings/clock/qcom,sm8150-camcc.h').read_text().splitlines():
    match = re.match(r'#define\s+(CAM_CC_MCLK1_CLK|TITAN_TOP_GDSC)\s+(\d+)', line)
    if match:
        constants[match[1]] = int(match[2])
assert cells(new[sensor]['power-domains']) == [handle(camcc), constants['TITAN_TOP_GDSC']]
assert cells(new[sensor]['clocks']) == cells(new[sensor]['assigned-clocks']) == [handle(camcc), constants['CAM_CC_MCLK1_CLK']]
assert cells(new[sensor]['assigned-clock-rates']) == [19200000]
assert cells(new[sensor]['reset-gpios']) == [handle(tlmm), 30, 1]
assert cells(new[sensor]['vana-supply']) == [handle(p + '/regulators/ldo4')]
assert cells(new[sensor]['vdig-supply']) == [handle(p + '/regulators/ldo1')]
assert cells(new[sensor]['vif-supply']) == [handle(vif)]
assert cells(new[tx]['data-lanes']) == [1, 2, 3, 4] and cells(new[rx]['data-lanes']) == [0, 1, 2, 3]
assert cells(new[rx]['clock-lanes']) == [7] and cells(new[rx]['bus-type']) == [4]
assert cells(new[tx]['remote-endpoint']) == [handle(rx)] and cells(new[rx]['remote-endpoint']) == [handle(tx)]
assert int.from_bytes(new[tx]['link-frequencies'], 'big') == 222000000
assert 'lane-polarities' not in new[tx] and 'lane-polarities' not in new[rx]
assert set(path for path in new if path.startswith(p + '/')) == {p + '/regulators', p + '/regulators/ldo1', p + '/regulators/ldo4'}
assert not any('supply' in name for name in new[p]) and 'realme,imx319-power-lab' in new[p]
assert cells(new[p + '/regulators/ldo1']['regulator-min-microvolt']) == [1100000]
assert cells(new[p + '/regulators/ldo1']['regulator-max-microvolt']) == [1104000]
assert cells(new[p + '/regulators/ldo4']['regulator-min-microvolt']) == [2800000]
assert cells(new[p + '/regulators/ldo4']['regulator-max-microvolt']) == [2800000]
pins = {}
for kind, pin, strength, function in [('mclk', 14, 6, 'cam_mclk'), ('reset', 30, 2, 'gpio')]:
    for state in ['active', 'sleep']:
        path = tlmm + '/camera-rear-' + kind + '-' + state + '-state'
        props = new[path]
        assert props['pins'] == ('gpio%d\0' % pin).encode()
        assert props['function'] == (function + '\0').encode() and cells(props['drive-strength']) == [strength]
        assert ('bias-disable' if state == 'active' else 'bias-pull-down') in props
        assert ('output-low' in props) == (kind == 'reset' and state == 'sleep')
        pins[kind, state] = path
for index, state in enumerate(['active', 'sleep']):
    assert cells(new[sensor]['pinctrl-' + str(index)]) == [handle(pins['mclk', state]), handle(pins['reset', state])]
expected_new = {p + '/regulators', p + '/regulators/ldo1', p + '/regulators/ldo4', sensor, sensor + '/port', tx,
                camss + '/ports/port@1', rx, *pins.values()}
# A pre-existing disabled bus/PHY port can gain only status/reg/phandle/endpoint.
expected_new -= old.keys()
assert set(semantic['only_new_nodes']) == expected_new and not semantic['only_old_nodes'], semantic
changed = {(item['path'], item['property']) for item in semantic['remaining_changed_properties']}
allowed = {(p, 'realme,imx319-power-lab'), (cci, 'status'), (bus, 'status'), (camss + '/ports/port@1', 'reg')}
assert changed <= allowed and (p, 'realme,imx319-power-lab') in changed, changed
report = dict(stage=235, source_sha256=sha(source), fragment_sha256=sha(R / 'imx319-p-lab.dtsi'),
              dtb_sha256=sha(dtb), dtb_bytes=dtb.stat().st_size, baseline_is_actual232_dtb=True,
              semantic_delta=semantic, strict_p_l1_l4_only=True,
              q_and_front_camera_and_other_existing_nodes_unchanged=True,
              actual_camcc_gdsc_mclk_gpio_supply_phandles_verified=True,
              original_cci0_master1_csiphy1_four_lane_graph_verified=True,
              original_pinctrl_strengths_and_sleep_states_verified=True,
              full_product_pmic_vin_schema_compliance_not_claimed=True, no_phone_operation=True)
(R / 'board-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
