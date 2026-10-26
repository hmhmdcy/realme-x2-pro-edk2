#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import libfdt

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
stage = Path('/home/cy122/pmos-samurai-kernel118/power132')
k = stage / 'kernel'
base = Path('/home/cy122/pmos-samurai-kernel129/kernel')
bin = Path(sys.executable).parent
out = Path('/mnt/e/edk2-samurai-out/kernel132/schema-test-r2')
out.mkdir(mode=0o700)
schema = k / 'Documentation/devicetree/bindings/power/supply/mps,mp2650.yaml'
processed = out / 'processed-mp2650-private.json'
results = []

def command(name, args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                       timeout=90, env=dict(os.environ, TMPDIR=str(stage)))
    log = p.stdout + p.stderr
    (out / (name + '-private.txt')).write_text(log)
    results.append(dict(name=name, exit=p.returncode, diagnostic_bytes=len(log.encode())))
    assert p.returncode == 0, (name, p.returncode)
    return log

assert command('doc', [bin / 'dt-doc-validate', '-u', k / 'Documentation/devicetree/bindings', schema]) == ''
assert command('compile', [bin / 'dt-mk-schema', '-j', '-o', processed, schema, schema.parent / 'power-supply.yaml']) == ''
props = 'compatible = "mps,mp2650"; reg = <0x5c>;'
cases = [('minimal', props, True),
         ('missing-reg', props.replace('reg = <0x5c>;', ''), False),
         ('unknown-property', props + ' unverified-policy = <1>;', False),
         ('extra-register', props.replace('<0x5c>', '<0x5c 0x5d>'), False),
         ('unsupported-fallback', props.replace('"mps,mp2650"', '"mps,mp2650", "mps,mp2659"'), False)]
checks = []
for name, properties, valid in cases:
    dts = out / (name + '.dts')
    dtb = out / (name + '.dtb')
    dts.write_text('/dts-v1/; / { #address-cells = <1>; #size-cells = <1>; '
                   'i2c@1000 { reg = <0x1000 0x100>; #address-cells = <1>; '
                   '#size-cells = <0>; charger@5c { ' + properties + ' }; }; };\n')
    command(name + '-dtc', [k / 'scripts/dtc/dtc', '-I', 'dts', '-O', 'dtb', '-o', dtb, dts])
    diagnostic = command(name, [bin / 'dt-validate', '-s', processed, '-l', 'mps,mp2650', dtb])
    assert bool(diagnostic) == (not valid), name
    if not valid:
        assert 'charger@5c' in diagnostic, name
    checks.append(dict(name=name, expected_valid=valid, diagnostic_present=bool(diagnostic), accepted_as_expected=True))

relative = Path('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')
candidate = k / relative
assert command('actual-board', [bin / 'dt-validate', '-s', processed, '-l', 'mps,mp2650', candidate]) == ''

def tree(path):
    fdt = libfdt.Fdt(path.read_bytes())
    answer = {}
    def walk(offset, name):
        properties = {}
        try:
            p = fdt.first_property_offset(offset)
            while True:
                prop = fdt.get_property_by_offset(p)
                properties[prop.name] = bytes(prop)
                p = fdt.next_property_offset(p)
        except libfdt.FdtException as exc:
            assert exc.err == -libfdt.NOTFOUND
        answer[name] = properties
        try:
            child = fdt.first_subnode(offset)
            while True:
                child_name = fdt.get_name(child)
                walk(child, name.rstrip('/') + '/' + child_name)
                child = fdt.next_subnode(child)
        except libfdt.FdtException as exc:
            assert exc.err == -libfdt.NOTFOUND
    walk(0, '/')
    return answer

old = tree(base / relative)
new = tree(candidate)
node = '/soc@0/geniqup@8c0000/i2c@884000/charger@5c'
assert set(new) - set(old) == {node}
assert not (set(old) - set(new))
assert all(new[name] == props for name, props in old.items())
assert new[node] == {'compatible': b'mps,mp2650\x00', 'reg': (0x5c).to_bytes(4, 'big')}
assert new[node.rsplit('/', 1)[0]]['clock-frequency'] == (400000).to_bytes(4, 'big')
report = dict(candidate=132, schema_checks=results, fixtures=checks,
              positive_cases=1, negative_cases=4, actual_board_node_valid=True,
              exactly_one_new_node=True, all_existing_nodes_and_property_bytes_unchanged=True,
              bus_clock_unchanged=400000, driver_unchanged=True,
              candidate_dtb_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
              charging_control_accepted=False, actual_deployment_pending=True)
(ref / 'power-schema-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K132_POWER_SCHEMA_AND_FULL_DTB_DIFFERENCE_PASS', flush=True)
