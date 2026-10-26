from pathlib import Path
import hashlib, json, struct, tarfile

archive = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'e3329db4f3568252286489abd2ae27b9cbd0c711a2c5d790ebfba80fffc5b56b'
with tarfile.open(archive) as source:
    files = {m.name.removeprefix('./'): source.extractfile(m).read() for m in source if m.isfile()}
phandles = {struct.unpack('>I', b)[0]: n.rsplit('/', 1)[0] for n, b in files.items() if n.endswith('/phandle') and len(b) == 4}
selected = {n.rsplit('/', 1)[0] for n, b in files.items() if n.endswith('/compatible') and
            (b'qca,wcn3990' in b or b'qcom,nq-nci' in b or 'qcom,qup_uart@0xc8c000' in n)}
selected |= {n.rsplit('/', 1)[0] for n in files if '/qcom,qup_uart@0xc8c000/' in n or '/i2c@a84000/' in n}
result = {}
for node in sorted(selected):
    props = {}
    for name, b in files.items():
        if name.rsplit('/', 1)[0] != node: continue
        key = name.rsplit('/', 1)[-1]
        if key in ('compatible', 'status', 'reg', 'interrupts', 'clock-frequency', 'qcom,wakeup-byte') or key.startswith('qcom,nq-') or 'supply' in key or 'voltage-level' in key:
            if key in ('compatible', 'status'):
                props[key] = b.decode().rstrip('\0').split('\0')
            else:
                assert len(b) % 4 == 0
                values = list(struct.unpack('>'+'I'*(len(b)//4), b))
                props[key] = values
                if values and values[0] in phandles and ('supply' in key or key.startswith('qcom,nq-')):
                    target = phandles[values[0]]
                    props[key] = {'cells': values, 'target': target}
                    if 'supply' in key:
                        props[key]['voltage'] = {k: struct.unpack('>I', files[target+'/'+k])[0]
                                                for k in ('regulator-min-microvolt', 'regulator-max-microvolt') if target+'/'+k in files}
    result[node] = props
assert any('qcom,nq-ven' in p and p['qcom,nq-ven']['cells'][1] == 36 for p in result.values())
out = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel92/stock-connectivity.json')
out.write_text(json.dumps({'source': 'same handset live Android DT, 2026-10-05', 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'nodes': result}, indent=2)+'\n')
print(out.read_text())
