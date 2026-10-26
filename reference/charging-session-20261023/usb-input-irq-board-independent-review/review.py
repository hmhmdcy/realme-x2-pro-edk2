"""Independent read/hash/format review; no author imports, tools or device access."""
from pathlib import Path
import hashlib
import json
import struct
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF / 'charging-ui-audit-20261023/usb-input-irq-board-candidate'
ORIGINAL = REF / 'charging-oem-audit-20261023/usb-input-irq-candidate'
PAIR_DIR = Path('E:/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01')
OLD_DTB = Path('E:/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def fdt(raw):
    h = struct.unpack_from('>10I', raw)
    assert h[0] == 0xd00dfeed and h[1] == len(raw)
    strings = raw[h[3]:h[3] + h[8]]
    reserve, pos = [], h[4]
    while True:
        entry = struct.unpack_from('>QQ', raw, pos)
        pos += 16
        if entry == (0, 0):
            break
        reserve.append(entry)
    pos, end, stack, nodes = h[2], h[2] + h[9], [], {}
    while pos < end:
        tag = struct.unpack_from('>I', raw, pos)[0]
        pos += 4
        if tag == 1:
            zero = raw.index(0, pos, end)
            stack.append(raw[pos:zero].decode())
            pos = (zero + 4) & ~3
            path = '/' + '/'.join(stack[1:])
            assert path not in nodes
            nodes[path] = {}
        elif tag == 2:
            stack.pop()
        elif tag == 3:
            size, offset = struct.unpack_from('>II', raw, pos)
            pos += 8
            zero = strings.index(0, offset)
            name = strings[offset:zero].decode()
            path = '/' + '/'.join(stack[1:])
            assert name not in nodes[path]
            nodes[path][name] = raw[pos:pos + size]
            pos = (pos + size + 3) & ~3
        elif tag == 4:
            pass
        elif tag == 9:
            assert not stack
            break
        else:
            raise AssertionError(('bad FDT tag', tag))
    return nodes, reserve, (h[5], h[6], h[7])


def elf(raw):
    assert raw[:6] == b'\x7fELF\x02\x01'
    assert struct.unpack_from('<H', raw, 16)[0] == 1
    assert struct.unpack_from('<H', raw, 18)[0] == 183
    offset = struct.unpack_from('<Q', raw, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', raw, 58)
    assert size == 64
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * size) for i in range(count)]
    def data(row):
        return raw[row[4]:row[4] + row[5]]
    names = data(sections[names_index])
    named = {names[row[0]:names.index(0, row[0])].decode(): row for row in sections}
    strong, weak = set(), set()
    for row in sections:
        if row[1] != 2:
            continue
        symbols, strings = data(row), data(sections[row[6]])
        assert row[9] == 24
        for pos in range(0, len(symbols), 24):
            name, info, other, index, value, length = struct.unpack_from('<IBBHQQ', symbols, pos)
            if not name or index != 0:
                continue
            symbol = strings[name:strings.index(0, name)].decode()
            if info >> 4 == 1:
                strong.add(symbol)
            elif info >> 4 == 2:
                weak.add(symbol)
    modinfo = [item.decode() for item in data(named['.modinfo']).split(b'\0') if item]
    return strong, weak, modinfo


delivery_raw = (AUTHOR / 'delivery.json').read_bytes()
assert sha(delivery_raw) == '6a6a727dc1de1601fea8aecc7ebda1def85f84a5ada46e03594a6c30b0effc51'
delivery = json.loads(delivery_raw)
assert delivery['passed'] and delivery['frozen'] and not delivery['device_accepted']
for name, expected in delivery['files'].items():
    assert sha((AUTHOR / name).read_bytes()) == expected, name
pair = json.loads((AUTHOR / 'pair-manifest.json').read_bytes())
assert sha((AUTHOR / 'pair-manifest.json').read_bytes()) == delivery['pair_manifest_sha256']
assert pair['required_together'] and pair['new_DTB_must_not_be_used_with_old_R7_module']
assert not pair['runtime_deployment_guard_or_cohort']
for field in ['native_DTB', 'USB_module']:
    row = pair[field]
    body = Path(row['private_path']).read_bytes()
    assert sha(body) == row['sha256'] and len(body) == row['bytes']
for name, expected in pair['receipts'].items():
    assert sha((AUTHOR / name).read_bytes()) == expected
dt = json.loads((AUTHOR / 'dt-result.json').read_bytes())
ko = json.loads((AUTHOR / 'ko-result.json').read_bytes())
execution = json.loads((AUTHOR / 'execution-receipt.json').read_bytes())
assert dt['passed'] and ko['passed'] and execution['passed']
assert sha((AUTHOR / 'compile-dt.py').read_bytes()) == dt['script_sha256']
assert sha((AUTHOR / 'build-ko.py').read_bytes()) == ko['builder_sha256']

old_raw = OLD_DTB.read_bytes()
new_raw = (PAIR_DIR / 'samurai-usb-input-irq-native-private.dtb').read_bytes()
assert sha(old_raw) == dt['source_native_sha256'] == pair['native_DTB']['source_native_sha256']
old, old_reserve, old_meta = fdt(old_raw)
new, new_reserve, new_meta = fdt(new_raw)
parent = '/soc@0/spmi@c440000/pmic@2'
child = parent + '/usb-input@1300'
assert len(old) == 965 and len(new) == 966 and sum(map(len, old.values())) == 3965
assert set(new) - set(old) == {child} and all(new[p] == props for p, props in old.items())
expected = {'compatible': b'realme,rmx1931-usb-input\0', 'reg': bytes.fromhex('00001300'),
            'interrupts': bytes.fromhex('0000000200000013000000040000000300000002000000130000000600000001'),
            'interrupt-names': b'usbin-plugin\0usbin-src-change\0', 'status': b'okay\0'}
assert new[child] == expected and old_reserve == new_reserve and old_meta == new_meta
assert old[parent]['#address-cells'] == bytes.fromhex('00000001') and old[parent]['#size-cells'] == bytes(4)
assert int.from_bytes(old[parent]['reg'][:4], 'big') == 2 and b'qcom,pm8150b' in old[parent]['compatible'].split(b'\0')
assert '#interrupt-cells' not in old[parent] and 'interrupt-parent' not in old[parent]
spmi = old['/soc@0/spmi@c440000']
assert 'interrupt-controller' in spmi and spmi['#interrupt-cells'] == bytes.fromhex('00000004')
assert 'interrupt-parent' not in new[child]
assert [p for p, props in new.items() if props.get('compatible') == expected['compatible']] == [child]
assert all(new[p].get('status', b'okay\0') in (b'okay\0', b'ok\0') for p in ['/', '/soc@0', '/soc@0/spmi@c440000', parent, child])
assert new[parent + '/typec@1500']['status'] == b'disabled\0'
eud = {p: props for p, props in new.items() if b'eud' in props.get('compatible', b'')}
assert eud and all(props['status'] == b'disabled\0' for props in eud.values())

source = (ORIGINAL / 'samurai-usb-input.c').read_bytes()
decoder = (ORIGINAL / 'samurai-usb-input-decode.h').read_bytes()
assert sha(source) == ko['source_sha256'] == pair['USB_module']['source_sha256']
assert sha(decoder) == ko['decoder_sha256'] == pair['USB_module']['decoder_sha256']
prior_path = HERE.parent / 'usb-input-irq-independent-review/review-result.json'
prior = json.loads(prior_path.read_bytes())
assert sha(source) == prior['source_sha256'] and sha(decoder) == prior['decoder_sha256']
assert ko['before'] == ko['after'] and ko['tracked_shared_R7_Image502_inputs_unchanged']
assert all(c['terminal'] and c['returncode'] == 0 for c in dt['commands'] + ko['commands'])
assert [p['target'] for p in ko['phases']] == ['modules_prepare', 'drivers/power/supply/samurai-usb-input.ko']
assert ko['diagnostics'] == [] and ko['Image502_export_count'] == 15097
assert ko['imports_all_from_Image502_builtin'] and ko['no_module_provider_fallback']
assert ko['Image502_build_receipt_sha256'] == pair['Image502_reference']['build_receipt_sha256']
assert sha((AUTHOR.parent / 'gauge-image502-notify-candidate/build-result.json').read_bytes()) == ko['Image502_build_receipt_sha256']
assert execution['module_native_exec_session'] == 59826 and execution['module_child_PIDs'] == [1022, 2880]
assert execution['same_original_module_exec_handle_waited'] and not execution['active_make_compiler_storage_process_remaining']
strong, weak, modinfo = elf((PAIR_DIR / 'samurai-usb-input-irq-private.ko').read_bytes())
assert len(strong) == ko['strong_import_count'] == 44 and not weak
assert 'intree=Y' in modinfo and 'depends=' in modinfo
assert 'alias=of:N*T*Crealme,rmx1931-usb-input' in modinfo
assert any(s.startswith('vermagic=7.3.0-rc6-rmx1931-samurai-k363+ ') for s in modinfo)

source_read = json.loads((AUTHOR / 'source-read-result.json').read_bytes())
for name, row in source_read['files'].items():
    assert sha((AUTHOR / 'source-reference' / name.replace('/', '--')).read_bytes()) == row['snapshot_sha256'] == row['sha256']
pmic_text = (AUTHOR / 'source-reference/drivers--mfd--qcom-spmi-pmic.c').read_text()
of_text = (AUTHOR / 'source-reference/drivers--of--platform.c').read_text()
assert 'return devm_of_platform_populate(&sdev->dev);' in pmic_text
assert 'of_platform_populate(dev->of_node, NULL, NULL, dev)' in of_text
assert 'of_platform_bus_create(child, matches, lookup, parent, true)' in of_text
binding = json.loads((AUTHOR / 'binding-result.json').read_bytes())
assert binding['passed'] and not binding['physical_bind_IRQ_allocation_or_delivery_attested']
result = {
    'verdict': 'no_new_blocker_in_offline_board_pair_scope',
    'author_delivery_sha256': sha(delivery_raw),
    'pair_sha256': sha((AUTHOR / 'pair-manifest.json').read_bytes()),
    'author_receipts': pair['receipts'],
    'prior_driver_review_reused_sha256': sha(prior_path.read_bytes()),
    'independent_raw_DTB_check': {'old_nodes': len(old), 'old_raw_properties': sum(map(len, old.values())),
                                  'added_node': child, 'only_five_exact_properties': True,
                                  'old_nodes_reserves_versions_exact': True, 'SPMI_4cell_parent_inheritance': True,
                                  'EUD_TypeC_disabled_unchanged': True},
    'independent_ELF_check': {'AArch64_ELF64LE_relocatable': True, 'strong_undefined': sorted(strong),
                             'weak_undefined': sorted(weak), 'modinfo_intree_alias_vermagic_checked': True},
    'source_creation_chain': 'PM8150B actual regmap then devm_of_platform_populate; direct enabled child on platform bus with actual PMIC parent; exact provider probe and single-node duplicate gate',
    'terminal_build_evidence': {'native_exec_session': 59826, 'child_PIDs': [1022, 2880], 'all_rc0': True,
                                'W1_clean': True, 'tracked_inputs_unchanged': True},
    'limits': ['Source matching is not actual probe or IRQ delivery.',
               '44 imports are independently counted in ELF; membership uses the frozen actual Image502 builtin export-map receipt.',
               'Both missing optional IRQs can still use original 1-second polling; loading is not IRQ acceptance.',
               'New DT and new duplicate-aware module form one offline pair; no boot/R9 cohort or device changes prepared.'],
    'author_tools_tests_build_storage_or_device_entrypoints_executed_by_reviewer': False,
    'physical_IRQ_or_latency_accepted': False,
    'reviewer_sha256': sha(Path(__file__).read_bytes())
}
output = HERE / 'review-result.json'
with output.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({'verdict': result['verdict'], 'review_result_sha256': sha(output.read_bytes())}))
