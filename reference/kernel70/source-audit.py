"""Offline PM8009 audit of existing sources, DTB and saved Android evidence."""
from pathlib import Path
import gzip, hashlib, json, re, struct, subprocess, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel70')
kernel = Path('/home/cy122/x2pro-linux/linux')
stock = Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
stock_commit = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
android = stock.parent.parent / 'artifacts/device/20261005T074931Z'
sources = {}

def snapshot(name, data, origin):
    (out / (name + '.source.gz')).write_bytes(gzip.compress(data, mtime=0))
    sources[name] = {'origin': origin, 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()}

for name, rel in [
    ('cmd-db-driver', 'drivers/soc/qcom/cmd-db.c'),
    ('rpmh-regulator-driver', 'drivers/regulator/qcom-rpmh-regulator.c'),
    ('samurai-before', 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),
    ('mtp', 'arch/arm64/boot/dts/qcom/sm8150-mtp.dts'),
    ('kernel-config', '.config'),
    ('rmi4-binding', 'Documentation/devicetree/bindings/input/syna,rmi4.yaml'),
    ('rmi4-kconfig', 'drivers/input/rmi4/Kconfig'),
]:
    snapshot(name, (kernel / rel).read_bytes(), str(kernel / rel))

for name, rel in [
    ('stock-19781-regulators', 'arch/arm64/boot/dts/19781/sm8150-regulator.dtsi'),
    ('stock-19781-pmic-overlay', 'arch/arm64/boot/dts/19781/sm8150-pmic-overlay.dtsi'),
    ('stock-19781-pm8009', 'arch/arm64/boot/dts/19781/pm8009.dtsi'),
    ('stock-19781-soc', 'arch/arm64/boot/dts/19781/sm8150.dtsi'),
    ('stock-19781-mtp', 'arch/arm64/boot/dts/19781/sm8150-mtp.dtsi'),
    ('stock-rpmh-regulator-driver', 'drivers/regulator/rpmh-regulator.c'),
]:
    data = subprocess.check_output(['git', '--git-dir=' + str(stock), 'show', stock_commit + ':' + rel])
    snapshot(name, data, {'commit': stock_commit, 'path': rel})

def parse_fdt(data):
    magic, total, off_struct, off_strings, _, _, _, _, size_strings, size_struct = struct.unpack_from('>10I', data)
    assert magic == 0xd00dfeed and total == len(data)
    strings = data[off_strings:off_strings + size_strings]
    end = off_struct + size_struct
    pos, stack, nodes = off_struct, [], {}
    while pos < end:
        token = struct.unpack_from('>I', data, pos)[0]
        pos += 4
        if token == 1:
            nul = data.index(0, pos, end)
            stack.append(data[pos:nul].decode())
            pos = (nul + 4) & ~3
            nodes.setdefault('/' + '/'.join(stack[1:]), {})
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, name_off = struct.unpack_from('>II', data, pos)
            pos += 8
            key = strings[name_off:strings.index(0, name_off)].decode()
            nodes['/' + '/'.join(stack[1:])][key] = data[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif token == 4:
            pass
        elif token == 9:
            assert not stack
            return nodes
        else:
            raise AssertionError(('FDT token', token, pos))
    raise AssertionError('No FDT end')

def decode(value):
    if not value:
        return True
    if value[0] != 0 and value.endswith(b'\0') and all(c == 0 or 32 <= c < 127 for c in value):
        return value.rstrip(b'\0').decode().split('\0')
    if len(value) % 4 == 0:
        return [f'0x{x:x}' for x in struct.unpack('>' + 'I' * (len(value) // 4), value)]
    return {'hex': value.hex()}

def pm8009_report(nodes):
    phandles = {struct.unpack('>I', p[k])[0]: path for path, p in nodes.items()
                for k in ('phandle', 'linux,phandle') if len(p.get(k, b'')) == 4}
    def available(path):
        parts = path.strip('/').split('/')
        for i in range(len(parts) + 1):
            p = '/' + '/'.join(parts[:i])
            if nodes.get(p, {}).get('status', b'okay\0') not in (b'okay\0', b'ok\0'):
                return False
        return True
    selected = {}
    for path, props in nodes.items():
        joined = path.encode() + b' '.join(props.get(k, b'') for k in ('compatible', 'regulator-name', 'qcom,resource-name'))
        if b'pm8009' in joined or re.search(rb'(ldof[256]|smpf2)', joined) or any(
                b'pm8009-rpmh-regulators' in p.get('compatible', b'') and path.startswith(parent + '/')
                for parent, p in nodes.items()):
            selected[path] = {'available': available(path),
                'properties': {k: decode(v) for k, v in props.items()
                    if k in ('compatible', 'reg', 'regulator-name', 'qcom,resource-name', 'qcom,pmic-id', 'status', 'phandle', 'linux,phandle', 'regulator-min-microvolt', 'regulator-max-microvolt')}}
    selected_phandles = {h: path for h, path in phandles.items()
                         if path in selected or any(path.startswith(p.rstrip('/') + '/') for p in selected)}
    consumers = []
    for path, props in nodes.items():
        for key, value in props.items():
            if key.endswith('-supply') and len(value) == 4:
                ref = struct.unpack('>I', value)[0]
                if ref in selected_phandles:
                    consumers.append({'path': path, 'available': available(path),
                                      'property': key, 'provider': selected_phandles[ref]})
    return {'nodes': selected, 'supply_consumers': consumers}

dtb_path = kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
dtb = dtb_path.read_bytes()
assert hashlib.sha256(dtb).hexdigest() == '4641207124f1276f00749132d118ba73c3fdeaef24aeac8b2b1df017ef5dea9a'
snapshot('active-firmware-dtb', dtb, str(dtb_path))
mainline_nodes = parse_fdt(dtb)
mainline = pm8009_report(mainline_nodes)

tar_path = android / 'live-device-tree.tar'
with tarfile.open(tar_path) as archive:
    props = {'/' + m.name.removeprefix('./').strip('/'): archive.extractfile(m).read()
             for m in archive if m.isfile()}
android_nodes = {}
for path, value in props.items():
    parent, _, key = path.rpartition('/')
    android_nodes.setdefault(parent or '/', {})[key] = value
old_android = pm8009_report(android_nodes)
old_touch = {path: {k: decode(v) for k, v in props.items() if len(v) < 512}
             for path, props in android_nodes.items() if 'synaptics19081@20' in path}
android_ids = {struct.unpack('>I', p[k])[0]: path for path, p in android_nodes.items()
               for k in ('phandle', 'linux,phandle') if len(p.get(k, b'')) == 4}
touch_routes = []
for path, props in android_nodes.items():
    if 'synaptics19081@20' not in path:
        continue
    for key in ('irq-gpio', 'reset-gpio', 'enable1v8_gpio', 'vdd_2v8-supply'):
        value = props.get(key, b'')
        if len(value) >= 4:
            provider = android_ids[struct.unpack_from('>I', value)[0]]
            touch_routes.append({'property': key, 'provider': provider,
                'provider_properties': {k: decode(v) for k, v in android_nodes[provider].items()
                    if k in ('compatible', 'reg', 'regulator-name', 'regulator-min-microvolt', 'regulator-max-microvolt')}})
identity = {k: decode(android_nodes['/'][k]) for k in ('model', 'compatible', 'oppo,dtsi_no', 'qcom,board-id')}
old_log = (android / 'dmesg.txt').read_bytes()
old_log_matches = [line for line in old_log.decode(errors='replace').splitlines()
                   if re.search(r'pm8009|ldof[256]|smpf2|PMIC@SID', line, re.I)]
cmd = (out / 'cmd-db.validated.txt').read_text()
resources = re.findall(r'^0x([0-9a-f]+): (\S+)', cmd, re.M)
f_resources = [(a, n) for a, n in resources if re.fullmatch(r'(ldo|smp)f\d+', n)]
assert cmd.startswith('afbbf870-b998-43d8-ab3d-42b3c68c0122\n0\nCommand DB DUMP\n')
report = {'sources': sources, 'stock_commit': stock_commit,
    'stock_remote': subprocess.check_output(['git', '--git-dir=' + str(stock), 'remote', 'get-url', 'origin']).decode().strip(),
    'android_archive': {'path': str(tar_path), 'bytes': tar_path.stat().st_size,
        'sha256': hashlib.sha256(tar_path.read_bytes()).hexdigest(), 'identity': identity},
    'android_dmesg': {'bytes': len(old_log), 'sha256': hashlib.sha256(old_log).hexdigest(),
        'first_line': old_log.decode(errors='replace').splitlines()[0], 'pm8009_matches': old_log_matches,
        'limit': 'Starts after 457 seconds; absence of a boot message is not proof of no boot failure.'},
    'active_mainline_dtb': mainline, 'old_android_live_dt': old_android,
    'touch_prerequisites': {'old_android_nodes': old_touch, 'old_android_routes': touch_routes,
        'current_i2c17_dt': {path: {k: decode(v) for k, v in props.items() if k in ('compatible', 'reg', 'status')}
            for path, props in mainline_nodes.items() if path.endswith('/i2c@c80000')},
        'native_touch_described': any(b'syna,rmi4' in props.get('compatible', b'')
                                     for props in mainline_nodes.values()),
        'current_config': [line for line in (kernel / '.config').read_text().splitlines()
            if re.match(r'CONFIG_I2C(=|_CHARDEV=|_QCOM_GENI=)|# CONFIG_RMI4_CORE', line)],
        'limit': 'No RMI4 controller identity/query, power sequence or input-event test has been performed.'},
    'cmd_db': {'entries': len(resources), 'unique_ids': len(set(n for _, n in resources)),
        'f_resources': f_resources, 'slaves': re.findall(r'^Slave .+$', cmd, re.M)},
    'limits': ['RPMh resource absence does not prove physical PM8009 absence.',
               'The saved Android tree is from 2026-10-05, not a fresh Android boot.',
               'No voltage, regulator enable, SPMI register, EUD control or USB gadget writes.']}
(out / 'source-audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({'cmd_db': report['cmd_db'], 'mainline': mainline,
                  'old_android_live_dt': old_android, 'old_android_identity': identity}, indent=2))
