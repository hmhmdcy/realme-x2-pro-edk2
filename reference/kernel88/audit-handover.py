from pathlib import Path
import hashlib, json, os, re, struct, subprocess, tarfile

K = Path('/home/cy122/x2pro-linux/linux')
I = Path('/home/cy122/x2pro-linux/initramfs')
O = Path('/mnt/e/edk2-samurai-out/kernel88')
W = Path('/mnt/e/RealmeX2Pro edk2')
R = W / 'reference/kernel88'
repo = Path('/home/cy122/edk2-samurai/repo')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = json.loads((O / 'preserved-before.json').read_text())
dts_path = 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
for rel, record in before['sources'].items():
    now = {'sha256': sha(K / rel), 'mode': (K / rel).stat().st_mode & 0o777}
    assert now['mode'] == record['mode'], rel
    if rel != dts_path:
        assert now == record, rel
    else:
        assert now['sha256'] != record['sha256'], rel
for rel, record in before['initramfs_files'].items():
    assert {'sha256': sha(I / rel), 'mode': (I / rel).stat().st_mode & 0o777} == record, rel
for rel, target in before['initramfs_links'].items():
    assert os.readlink(I / rel) == target, rel
assert subprocess.check_output(['git', '-C', str(K), 'rev-parse', 'HEAD'], text=True).strip() == before['local_kernel_head']
assert sha(K / 'usr/initramfs_data.cpio') == before['cpio_sha256']
assert sha(K / '.config') == sha(O / 'config-wifi') == '981b4b828e5e6a8a108a7bff1c8fa7ccb8133abcf6ffd0ec0c631fbbca4f44ff'

def values(p):
    result = {}
    for line in p.read_text().splitlines():
        match = re.fullmatch(r'CONFIG_(\w+)=(.*)', line)
        if match:
            result[match[1]] = match[2]
        else:
            match = re.fullmatch(r'# CONFIG_(\w+) is not set', line)
            if match:
                result[match[1]] = 'n'
    return result

old_config, new_config = values(O / 'config-before'), values(K / '.config')
changes = {k: {'before': old_config.get(k, 'n'), 'candidate': new_config.get(k, 'n')}
           for k in old_config.keys() | new_config.keys() if old_config.get(k, 'n') != new_config.get(k, 'n')}
assert changes == json.loads((W / 'reference/kernel87/wifi-profile-audit.json').read_text())['changed_symbols']
assert len(changes) == 27
subprocess.run(['git', '-C', str(K), 'apply', '--reverse', '--check', str(R / 'manual-mpss-node.patch')], check=True)

def fdt_nodes(data):
    assert data[:4] == bytes.fromhex('d00dfeed')
    total, offset, strings = struct.unpack_from('>III', data, 4)
    assert total == len(data)
    stack, nodes = [], {}
    while True:
        token = struct.unpack_from('>I', data, offset)[0]
        offset += 4
        if token == 1:
            end = data.index(0, offset)
            stack.append(data[offset:end].decode())
            offset = (end + 4) & ~3
            nodes['/'.join(stack)] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, name_offset = struct.unpack_from('>II', data, offset)
            offset += 8
            start = strings + name_offset
            name = data[start:data.index(0, start)].decode()
            nodes['/'.join(stack)][name] = data[offset:offset + size]
            offset = (offset + size + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            assert not stack
            return nodes
        else:
            raise AssertionError(token)

old_nodes = fdt_nodes((O / 'samurai-before.dtb').read_bytes())
new_nodes = fdt_nodes((O / 'samurai-wifi.dtb').read_bytes())
assert old_nodes.keys() == new_nodes.keys()
dt_changes = []
for node in old_nodes:
    for prop in old_nodes[node].keys() | new_nodes[node].keys():
        a, b = old_nodes[node].get(prop), new_nodes[node].get(prop)
        if a != b:
            dt_changes.append({'node': node, 'property': prop,
                               'before_hex': a.hex() if a is not None else None,
                               'after_hex': b.hex() if b is not None else None})
assert {(x['node'], x['property']) for x in dt_changes} == {
    ('/soc@0/remoteproc@4080000', 'status'), ('/soc@0/remoteproc@4080000', 'firmware-name')}
assert new_nodes['/soc@0/remoteproc@4080000']['status'] == b'okay\0'
assert new_nodes['/soc@0/remoteproc@4080000']['firmware-name'] == b'qcom/sm8150/realme/samurai/modem.mdt\0'
assert new_nodes['/soc@0/wifi@18800000']['status'] == b'disabled\0'
assert sha(K / 'arch/arm64/boot/Image') == sha(O / 'Image-wifi') == '02fbe7e5d20cc2a0f5b55e08511ee9a1a39d2c47516079569fe8dc2368360ea0'
image = (O / 'Image-wifi').read_bytes()
assert image[56:60] == b'ARM\x64' and b'#89 SMP PREEMPT' in image
assert not re.search(r'\b(?:warning|error):', (O / 'build-wifi.log').read_text())
tools = json.loads((O / 'tools-test-audit.json').read_text())
assert tools['audit'] == 'PASS' and tools['compile_exit'] == tools['run_exit'] == 0
for name, record in tools['tools'].items():
    assert sha(O / name) == record['sha256'] and (O / name).stat().st_size == record['bytes']
firmware = json.loads((O / 'mpss-firmware-manifest.json').read_text())
assert sha(O / 'mpss-firmware-stock.tar') == firmware['archive_sha256']
assert len(firmware['files']) == 33 and firmware['relocated_span_bytes'] == firmware['reserved_region_bytes'] == 0xa000000
domain = firmware['service_descriptions']['modemuw.jsn']['sr_domain']
assert domain == {'soc': 'msm', 'domain': 'modem', 'subdomain': 'wlan_pd', 'qmi_instance_id': 180}
mapper = (K / 'drivers/soc/qcom/qcom_pd_mapper.c').read_text()
assert 'msm/modem/wlan_pd' in mapper and 'wlan/fw' in mapper
pas = (K / 'drivers/remoteproc/qcom_q6v5_pas.c').read_text()
desc = pas[pas.index('static const struct qcom_pas_data mpss_resource_init = {'):]
assert '.auto_boot = false,' in desc[:700] and '.pas_id = 4,' in desc[:700]
assert '{ .compatible = "qcom,sm8150-mpss-pas", .data = &mpss_resource_init }' in pas

with tarfile.open(O / 'handover.tar') as archive:
    members = {Path(m.name).name.removeprefix('k88-'): archive.extractfile(m).read()
               for m in archive.getmembers() if m.isfile()}
for line in members['handover-hashes.txt'].decode().splitlines():
    digest, remote = line.split('  ', 1)
    name = Path(remote).name.removeprefix('k88-')
    assert hashlib.sha256(members[name]).hexdigest() == digest, name
for name, content in members.items():
    (O / name).write_bytes(content)
state = members['handover-state.txt'].decode()
assert state.startswith('32bf2d8f-8dde-47dc-9b88-e87db9e95198\n') and '#86 SMP PREEMPT' in state
assert state.splitlines()[3] == '0'
assert 'underrun:       0' in state and 'frame_done_cnt:2mode:' in state
assert 'snapshot:count=0\n0\n' in state
assert 'NETWORK_INTERFACES\nlo\nusb0\n' in state and '0-005c' not in state
snapshot_sha = hashlib.sha256(members['handover-snapshot.txt']).hexdigest()
assert snapshot_sha == '550d76908bd09bb280f57a5937fce7ec0101e4c167fed850b42834085e53f2f2'
assert sha(repo / 'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb') == '872fd9f83382143977c2406c0a869bcac5c051f0f27350ddf3676f043572587b'
for number, digest in [(85, 'b68efb3b534fc882972d1a7bbaced45e7dde78ae949584ba3d524cf917ecfb2a'),
                       (86, '74ea52c2f439f25a6f7cc8f1438dffb372e8c8d4845a790940c66b9bcf3f392f'),
                       (87, '7498b2fcc10f3fbd0c319e74f793b8413a2ab6872da7790c9591e26dd83e0b32')]:
    historical = W / f'reference/kernel{number}'
    assert sha(historical / 'SHA256SUMS') == digest
    for line in (historical / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha(historical / name) == expected

result = {'audit': 'PASS', 'scope': 'offline build, preservation, firmware integrity and read-only handset handover',
          'handset_kernel_build': 86, 'handset_boot_id': state.splitlines()[0],
          'handset_uptime_seconds': float(state.splitlines()[2].split()[0]), 'taint': 0,
          'display_timeouts': 2, 'display_underruns': 0, 'display_snapshot_sha256': snapshot_sha,
          'preserved_source_count': len(before['sources']),
          'initramfs_files': len(before['initramfs_files']), 'initramfs_links': len(before['initramfs_links']),
          'changed_source_paths': [dts_path], 'configuration_changes': changes,
          'dtb_semantic_changes': dt_changes, 'WiFi_node_enabled': False,
          'candidate': {'kernel_build': 89, 'bytes': len(image), 'sha256': sha(O / 'Image-wifi'), 'deployed': False,
                        'dtb_sha256': sha(O / 'samurai-wifi.dtb'), 'config_sha256': sha(K / '.config'),
                        'cpio_sha256': sha(K / 'usr/initramfs_data.cpio')},
          'tools_test': tools, 'MPSS_firmware_files_verified': 33,
          'MPSS_relocated_span_bytes': 0xa000000, 'MPSS_runtime_verified': False,
          'actual_chip_board_ID_known': False, 'wireless_scan_connection_traffic_verified': False,
          'EDK2_firmware_DT_changed_or_built': False, 'new_partition_write_or_reboot': False,
          'charging_control_verified': False, 'next_hardware_priority': 'Wi-Fi',
          'full_hardware_goal_completed': False, 'historical_85_86_87_manifests_unchanged': True}
(O / 'handover-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print('PASS: #89 built, only MPSS DTS/config changed; sources/initramfs preserved; handset still #86; no deployment.')
