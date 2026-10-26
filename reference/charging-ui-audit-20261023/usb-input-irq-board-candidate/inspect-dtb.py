"""Read the frozen native DTB; do not compile, overlay or access a device."""
from pathlib import Path
import hashlib
import json
import struct

HERE = Path(__file__).resolve().parent
DTB = Path('E:/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def decode(raw):
    header = struct.unpack_from('>10I', raw)
    magic, total, tree_off, strings_off, reserve_off, version, last_version, boot_cpu, string_size, tree_size = header
    assert magic == 0xd00dfeed and total == len(raw) and version == 17 and last_version <= 17
    assert tree_off + tree_size <= total and strings_off + string_size <= total
    strings = raw[strings_off:strings_off + string_size]
    offset, end, stack, nodes = tree_off, tree_off + tree_size, [], {}
    while offset < end:
        tag, = struct.unpack_from('>I', raw, offset)
        offset += 4
        if tag == 1:
            nul = raw.index(0, offset, end)
            name = raw[offset:nul].decode()
            stack.append(name)
            path = '/' + '/'.join(stack[1:])
            assert path not in nodes
            nodes[path] = {}
            offset = (nul + 4) & ~3
        elif tag == 2:
            assert stack
            stack.pop()
        elif tag == 3:
            size, name_offset = struct.unpack_from('>II', raw, offset)
            offset += 8
            assert name_offset < len(strings) and offset + size <= end
            nul = strings.index(0, name_offset)
            name = strings[name_offset:nul].decode()
            props = nodes['/' + '/'.join(stack[1:])]
            assert name not in props
            props[name] = raw[offset:offset + size]
            offset = (offset + size + 3) & ~3
        elif tag == 4:
            pass
        elif tag == 9:
            assert not stack
            break
        else:
            raise ValueError(tag)
    reserves, pos = [], reserve_off
    while True:
        address, size = struct.unpack_from('>QQ', raw, pos)
        pos += 16
        if not address and not size:
            break
        reserves.append((address, size))
    return {'nodes': nodes, 'reserves': reserves, 'boot_cpu': boot_cpu,
            'version': version, 'last_version': last_version}


def main():
    raw = DTB.read_bytes()
    assert sha(raw) == '9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
    tree = decode(raw)
    nodes = tree['nodes']
    controller = '/soc@0/spmi@c440000'
    parent = controller + '/pmic@2'
    assert nodes[controller]['#interrupt-cells'] == struct.pack('>I', 4)
    assert 'interrupt-controller' in nodes[controller]
    assert b'qcom,pm8150b\0' in nodes[parent]['compatible']
    assert nodes[parent]['reg'] == struct.pack('>II', 2, 0)
    assert nodes[parent]['#address-cells'] == struct.pack('>I', 1)
    assert nodes[parent]['#size-cells'] == struct.pack('>I', 0)
    assert nodes[parent].get('status', b'okay\0') in (b'okay\0', b'ok\0')
    assert nodes[controller].get('status', b'okay\0') in (b'okay\0', b'ok\0')
    assert not any(b'realme,rmx1931-usb-input\0' in props.get('compatible', b'') for props in nodes.values())
    assert nodes[parent + '/typec@1500']['status'] == b'disabled\0'
    disabled_eud = {path: props['status'].decode().strip('\0') for path, props in nodes.items()
                    if b'eud' in props.get('compatible', b'') and 'status' in props}
    assert disabled_eud and all(value == 'disabled' for value in disabled_eud.values())
    out = {'passed': True, 'native_DTB_sha256': sha(raw), 'native_DTB_bytes': len(raw),
           'node_count': len(nodes), 'reserve_map_count': len(tree['reserves']),
           'parent': parent, 'parent_enabled': True, 'controller_enabled': True,
           'parent_address_cells': 1, 'parent_size_cells': 0,
           'controller_interrupt_cells': 4, 'existing_custom_input_count': 0,
           'typec_disabled': True, 'EUD_disabled': disabled_eud,
           'DT_compiled_or_applied': False, 'device_access': False,
           'script_sha256': sha(Path(__file__).read_bytes())}
    (HERE / 'dtb-input-result.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
