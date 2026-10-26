from pathlib import Path
import hashlib, json, struct

stage = Path('/home/cy122/pmos-samurai-kernel113')
base = Path('/home/cy122/pmos-samurai-kernel112')
out = Path('/mnt/e/edk2-samurai-out/kernel113')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = (out / 'config-before').read_text()
after = (out / 'config-after').read_text()
assert before == (base / 'kernel/.config').read_text()
assert after.count('CONFIG_SAMURAI_SENSOR_POWER=y\n') == 1
normalized = after.replace('CONFIG_SAMURAI_SENSOR_POWER=y\n', '').replace(str(stage / 'initramfs'), str(base / 'initramfs'))
assert normalized == before, 'Unexpected config delta'
for path in (base / 'initramfs').rglob('*'):
    new = stage / 'initramfs' / path.relative_to(base / 'initramfs')
    if path.is_symlink(): assert new.is_symlink() and new.readlink() == path.readlink()
    elif path.is_file(): assert path.read_bytes() == new.read_bytes()
for name in ('samurai-sensor-power.c', 'samurai-sensor-power-seq.h'):
    assert sha(ref / name) == sha(stage / 'kernel/drivers/misc' / name)
for name in ('drivers/misc/fastrpc.c', 'drivers/remoteproc/qcom_q6v5_pas.c',
             'drivers/soc/qcom/qcom_pd_mapper.c', 'drivers/gpu/drm/panel/panel-samsung-sofef03f.c'):
    assert sha(stage / 'kernel' / name) == sha(base / 'kernel' / name)
assert b'#113 SMP PREEMPT' in (out / 'Image-sensor-power').read_bytes()
assert 'warning:' not in (out / 'sensor-power-build-w1.log').read_text()
assert 'PASS: actual supply sequence' in (out / 'test-sensor-power.log').read_text()
board = 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert (stage / 'kernel' / board).read_text().startswith((base / 'kernel' / board).read_text())

def fdt(path):
    data = path.read_bytes()
    magic, total, soff, stroff = struct.unpack_from('>4I', data)
    assert magic == 0xd00dfeed and total == len(data)
    nodes, stack, off = {}, [], soff
    while True:
        token, = struct.unpack_from('>I', data, off); off += 4
        if token == 1:
            end = data.index(0, off); name = data[off:end].decode(); off = (end + 4) & ~3
            stack.append(name); nodes['/' + '/'.join(stack[1:])] = {}
        elif token == 2: stack.pop()
        elif token == 3:
            size, noff = struct.unpack_from('>2I', data, off); off += 8
            end = data.index(0, stroff + noff); name = data[stroff + noff:end].decode()
            nodes['/' + '/'.join(stack[1:])][name] = data[off:off + size]
            off = (off + size + 3) & ~3
        elif token == 4: pass
        elif token == 9: break
        else: raise AssertionError('Unknown FDT token')
    return nodes

nodes = fdt(out / 'dtb-sensor-power')
old = fdt(out.parent / 'kernel112/dtb-startup')
assert set(nodes) - set(old) == {'/sensor-power'}
assert not set(old) - set(nodes)
for name, props in old.items():
    for key, value in props.items():
        assert nodes[name].get(key) == value, (name, key)
    assert set(nodes[name]) - set(props) <= {'phandle'}, name
lookup = {struct.unpack('>I', p['phandle'])[0]: name for name,p in nodes.items() if 'phandle' in p}
power = nodes['/sensor-power']
assert power['compatible'] == b'realme,samurai-sensor-power\0'
assert set(power) == {'compatible','vdd-supply','vddio-supply','remoteproc'}
resolved = {key:lookup[struct.unpack('>I',power[key])[0]] for key in ('vdd-supply','vddio-supply','remoteproc')}
for key, child in [('vdd-supply','ldo7'), ('vddio-supply','ldo8')]:
    path = resolved[key]; assert path.endswith('/' + child)
    parent = nodes[path.rsplit('/',1)[0]]
    assert b'qcom,pm8150l-rpmh-regulators\0' in parent['compatible']
    assert parent['qcom,pmic-id'] == b'c\0'
assert resolved['remoteproc'].endswith('/remoteproc@2400000')
report = dict(kernel_audit_pass=True, kernel_build=113, baseline=112,
              config_delta=['CONFIG_INITRAMFS_SOURCE','CONFIG_SAMURAI_SENSOR_POWER'],
              initramfs_bytes_unchanged=True, sensor_sequence_asan_ubsan_pass=True,
              driver_w1_compile_pass=True, supply_phandles_resolve_to_pm8150l_l7_l8=True,
              new_dtb_nodes=1, existing_nodes_preserved=True, slpi_auto_boot=False,
              existing_dtb_properties_preserved=True,
              image_sha256=sha(out / 'Image-sensor-power'), dtb_sha256=sha(out / 'dtb-sensor-power'),
              cpio_sha256=sha(out / 'cpio-sensor-power'), candidate_deployed=False,
              sensor_function_accepted=False, userdata_reformatted=False, goal_complete=False)
(out / 'kernel-validation.json').write_text(json.dumps(report, indent=2)+'\n')
(ref / 'kernel-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print('KERNEL113_SOURCE_CONFIG_INITRAMFS_DRIVER_DTB_SUPPLIES_AUDIT_PASS; NOT_DEPLOYED')
