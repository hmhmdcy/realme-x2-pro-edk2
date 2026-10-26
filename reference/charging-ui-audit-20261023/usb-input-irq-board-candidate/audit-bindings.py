"""Bind the actual PMIC/OF creation path to this single new DT child."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF / 'charging-oem-audit-20261023/usb-input-irq-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def function(text, name):
    pos = text.index(name + '(')
    start = text.rfind('\n', 0, pos) + 1
    offset = text.index('{', pos) + 1
    depth = 1
    while depth:
        depth += (text[offset] == '{') - (text[offset] == '}')
        offset += 1
    return text[start:offset]


sources = json.loads((HERE / 'source-read-result.json').read_bytes())
assert sources['passed']
for path, row in sources['files'].items():
    assert sha(HERE / 'source-reference' / path.replace('/', '--')) == row['sha256']
pmic = (HERE / 'source-reference/drivers--mfd--qcom-spmi-pmic.c').read_text()
of = (HERE / 'source-reference/drivers--of--platform.c').read_text()
usb = (AUTHOR / 'samurai-usb-input.c').read_text()
assert sha(AUTHOR / 'samurai-usb-input.c') == '0fdafb8b3924e431efd67a888cbb88b8f5fe6de22dc400b009bf64cba34b7be5'
parent_probe = function(pmic, 'pmic_spmi_probe')
ordered = ['devm_regmap_init_spmi_ext', 'pmic_spmi_load_revid',
           'spmi_device_set_drvdata(sdev, ctx)', 'return devm_of_platform_populate(&sdev->dev);']
assert [parent_probe.index(token) for token in ordered] == sorted(parent_probe.index(token) for token in ordered)
assert '{ .compatible = "qcom,pm8150b", .data = N_USIDS(2) }' in pmic
populate = function(of, 'devm_of_platform_populate')
assert 'of_platform_populate(dev->of_node, NULL, NULL, dev)' in populate
walk = function(of, 'of_platform_populate')
assert 'for_each_child_of_node_scoped(root, child)' in walk
assert 'of_platform_bus_create(child, matches, lookup, parent, true)' in walk
create = function(of, 'of_platform_bus_create')
assert 'of_platform_device_create_pdata(bus, bus_id, platform_data, parent)' in create
leaf = function(of, 'of_platform_device_create_pdata')
assert 'if (!of_device_is_available(np) ||' in leaf
assert 'of_device_alloc(np, bus_id, parent)' in leaf
assert 'dev->dev.bus = &platform_bus_type' in leaf and 'of_device_add(dev)' in leaf
alloc = function(of, 'of_device_alloc')
assert 'platform_device_set_of_node(dev, np)' in alloc and 'dev->dev.parent = parent ? : &platform_bus' in alloc
probe = function(usb, 'samurai_usb_probe')
for token in ['of_machine_is_compatible("realme,samurai")',
              'of_device_is_compatible(dev->parent->of_node, "qcom,pm8150b")',
              'of_node_name_eq(dev->parent->of_node, "pmic")',
              'of_property_read_u32(dev->parent->of_node, "reg", &base) || base != 2',
              'device_property_read_u32(dev, "reg", &base) || base != 0x1300',
              'dev_get_regmap(dev->parent, NULL)']:
    assert token in probe
assert '{ .compatible = "realme,rmx1931-usb-input" }' in usb
init = function(usb, 'samurai_usb_init')
assert init.index('of_find_compatible_node') < init.index('if (available)') < init.index('platform_device_register_full')
dt = json.loads((HERE / 'dt-result.json').read_bytes())
assert dt['passed'] and dt['old_node_count'] == 965 and dt['new_node_count'] == 966
assert dt['only_added_node'] == '/soc@0/spmi@c440000/pmic@2/usb-input@1300'
assert dt['added_properties']['compatible'] == b'realme,rmx1931-usb-input\0'.hex()
assert dt['added_properties']['reg'] == '00001300'
result = {'passed': True, 'scope': 'actual source call/matching path and exact DT bytes; not executing Linux probe',
          'PM8150B_SID2_probe_map_before_populate': True,
          'direct_enabled_compatible_child_created_on_platform_bus': True,
          'direct_parent_and_fwnode_preserved': True, 'child_matches_actual_provider_gate': True,
          'single_available_node_suppresses_software_board_duplicate': True,
          'source_tree_receipt_sha256': sha(HERE / 'source-read-result.json'),
          'DT_receipt_sha256': sha(HERE / 'dt-result.json'),
          'source_function_sha256': {name: hashlib.sha256(body.encode()).hexdigest() for name, body in [
              ('pmic_spmi_probe', parent_probe), ('devm_of_platform_populate', populate),
              ('of_platform_populate', walk), ('of_platform_bus_create', create),
              ('of_platform_device_create_pdata', leaf), ('of_device_alloc', alloc),
              ('samurai_usb_probe', probe), ('samurai_usb_init', init)]},
          'physical_bind_IRQ_allocation_or_delivery_attested': False,
          'script_sha256': sha(Path(__file__))}
(HERE / 'binding-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'binding_receipt_sha256': sha(HERE / 'binding-result.json')}))
