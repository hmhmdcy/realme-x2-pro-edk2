"""Read-only mapping of saved Android QUP1 wiring to the actual Linux tree."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel79')
k = Path('/home/cy122/x2pro-linux/linux')
repo = Path('/home/cy122/edk2-samurai/repo')
archive = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
with tarfile.open(archive) as tar:
    props = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
bus = next(p.rsplit('/', 1)[0] for p in props if p.endswith('/i2c@884000/compatible'))
selected = {p: v.hex() for p, v in props.items() if p.startswith(bus + '/')}
handles = [int.from_bytes(props[bus + '/pinctrl-0'][i:i+4], 'big')
           for i in range(0, len(props[bus + '/pinctrl-0']), 4)]
pin_nodes = []
for p, value in props.items():
    if p.endswith('/phandle') and int.from_bytes(value, 'big') in handles:
        parent = p.rsplit('/', 1)[0]
        pin_nodes.append({n: v.hex() for n, v in props.items() if n.startswith(parent + '/')})
sources = {}
for rel in ('arch/arm64/boot/dts/qcom/sm8150.dtsi',
            'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
            'drivers/i2c/busses/i2c-qcom-geni.c',
            'drivers/soc/qcom/qcom-geni-se.c', 'drivers/dma/qcom/gpi.c'):
    p = k / rel
    data = p.read_bytes()
    sources[rel] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    lines = data.decode().splitlines()
    indexes = set()
    pattern = (r'qupv3_id_0:|i2c1:|qup_i2c1_default:|gpi_dma0:' if rel.endswith('sm8150.dtsi')
               else r'^&(?:i2c|qupv3|gpi_dma)|geni_i2c_probe|geni_se_init|geni_se_select_mode|geni_se_config_packing|pm_runtime|geni_se_resources_on|GPI_INIT|gpi_probe')
    for i, line in enumerate(lines):
        if re.search(pattern, line):
            indexes.update(range(max(0, i-2), min(len(lines), i+22)))
    (out / (p.name + '.excerpts.txt')).write_text('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(indexes)) + '\n')
report = {'stock_archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'stock_bus': bus, 'stock_bus_properties_hex': selected,
          'stock_bus_pin_handles': handles, 'stock_bus_pin_nodes_hex': pin_nodes,
          'kernel_source_head': subprocess.check_output(['git', '-C', str(k), 'rev-parse', 'HEAD'], text=True).strip(),
          'repo_head': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
          'sources': sources}
(out / 'bus-source-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'stock_bus': bus, 'stock_bus_pin_handles': handles,
                  'stock_bus_pin_nodes_hex': pin_nodes, 'sources': sources}, indent=2))
