from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import libfdt
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
stage = Path('/home/cy122/pmos-samurai-build134/usb134')
k = stage / 'kernel'
base = Path('/home/cy122/pmos-samurai-kernel118/power132/kernel')
bin = Path(sys.executable).parent
out = Path('/mnt/e/edk2-samurai-out/kernel134/schema-test')
out.mkdir(mode=0o700)
schema = k / 'Documentation/devicetree/bindings/power/supply/realme,rmx1931-usb-input.yaml'
processed = out / 'processed-usb-input-private.json'
results = []
def command(name, args):
    p = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=90,
                       env=dict(os.environ, TMPDIR=str(stage)))
    text = p.stdout + p.stderr
    (out / (name + '-private.txt')).write_text(text)
    results.append(dict(name=name, exit=p.returncode, diagnostic_bytes=len(text.encode())))
    assert p.returncode == 0, (name, p.returncode)
    return text
assert command('doc', [bin / 'dt-doc-validate', '-u', k / 'Documentation/devicetree/bindings', schema]) == ''
assert command('compile', [bin / 'dt-mk-schema', '-j', '-o', processed, schema, schema.parent / 'power-supply.yaml']) == ''
props = 'compatible = "realme,rmx1931-usb-input"; reg = <0x1300>;'
cases = [('minimal', props, True), ('missing-reg', props.replace('reg = <0x1300>;', ''), False),
         ('wrong-base', props.replace('0x1300', '0x1400'), False),
         ('extra-register', props.replace('<0x1300>', '<0x1300 0x1500>'), False),
         ('unknown-policy', props + ' charging-current = <1500000>;', False),
         ('extra-compatible', props.replace('"realme,rmx1931-usb-input"', '"realme,rmx1931-usb-input", "qcom,qpnp-smb5"'), False)]
fixtures = []
for name, properties, valid in cases:
    dts, dtb = out / (name + '.dts'), out / (name + '.dtb')
    dts.write_text('/dts-v1/; / { #address-cells = <1>; #size-cells = <0>; '
                  'pmic@2 { reg = <2>; #address-cells = <1>; #size-cells = <0>; '
                  'usb-input@1300 { ' + properties + ' }; }; };\n')
    command(name + '-dtc', [k / 'scripts/dtc/dtc', '-I', 'dts', '-O', 'dtb', '-o', dtb, dts])
    diagnostic = command(name, [bin / 'dt-validate', '-s', processed, '-l', 'realme,rmx1931-usb-input', dtb])
    assert bool(diagnostic) == (not valid), name
    if not valid:
        assert 'usb-input@1300' in diagnostic
    fixtures.append(dict(name=name, expected_valid=valid, accepted_as_expected=True))
relative = Path('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')
assert command('actual-board', [bin / 'dt-validate', '-s', processed, '-l', 'realme,rmx1931-usb-input', k / relative]) == ''
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
                walk(child, name.rstrip('/') + '/' + fdt.get_name(child))
                child = fdt.next_subnode(child)
        except libfdt.FdtException as exc:
            assert exc.err == -libfdt.NOTFOUND
    walk(0, '/')
    return answer
old, new = tree(base / relative), tree(k / relative)
node = '/soc@0/spmi@c440000/pmic@2/usb-input@1300'
assert set(new) - set(old) == {node} and not set(old) - set(new)
assert all(new[name] == props for name, props in old.items())
assert new[node] == dict(compatible=b'realme,rmx1931-usb-input\0', reg=(0x1300).to_bytes(4, 'big'))
report = dict(candidate=134, schema_checks=results, fixtures=fixtures, positive_cases=1, negative_cases=5,
    actual_board_node_valid=True, exactly_one_new_usb_input_node=True,
    all_existing_nodes_and_property_bytes_unchanged=True, mp2650_and_typec_status_unchanged=True,
    candidate_dtb_sha256=hashlib.sha256((k / relative).read_bytes()).hexdigest(),
    binding_is_local_candidate_with_placeholder_maintainer=True, deployed=False, charging_control_accepted=False)
(ref / 'usb-schema-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_USB_SCHEMA_AND_COMPLETE_DTB_DIFFERENCE_PASS', flush=True)
