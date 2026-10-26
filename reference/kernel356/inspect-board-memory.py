"""Compare the matching Realme board memory source with retained DT artifacts."""
from pathlib import Path
import hashlib, importlib.util, json, re, struct, subprocess
import host

HERE = Path(__file__).resolve().parent
P = host.PRIVATE
spec = importlib.util.spec_from_file_location('storage284', HERE.parent/'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
build = storage.mounted_build()
ns = {}
exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0], ns)
parse = ns['fdt_nodes']
repo = Path('/home/cy122/x2pro-linux/refs/realme-x2pro-androidr-project-k112')
commit = '23172a1571bd91156032cc9fef16284a82b63d2c'
name = 'arch/arm64/boot/dts/19781/sm8150.dtsi'
raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit+':'+name])
assert raw == (P.parent/'kernel112/stock-hardware-reference/sm8150.dtsi').read_bytes()
source = re.sub(r'/\*.*?\*/|//[^\n]*', '', raw.decode(), flags=re.S)
match = re.search(r'pil_camera_mem:\s*camera_region\s*\{(.*?)\};', source, re.S)
assert match
reg = re.search(r'reg\s*=\s*<([^>]+)>', match[1])
cells = [int(x, 0) for x in reg[1].split()]
assert cells == [0, 0x9ab00000, 0, 0x500000]
physical, size = cells[1], cells[3]

dtb = build/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
blob = dtb.read_bytes()
nodes = parse(blob)
ranges = []
for path, props in nodes.items():
    if not path.startswith('/reserved-memory/') or 'reg' not in props:
        continue
    words = struct.unpack('>'+'I'*(len(props['reg'])//4), props['reg'])
    assert len(words)%4 == 0
    for i in range(0, len(words), 4):
        start = words[i]*2**32+words[i+1]; length = words[i+2]*2**32+words[i+3]
        ranges.append(dict(path=path, start=start, size=length, no_map='no-map' in props,
                           contains_board_camera=start<=physical and start+length>=physical+size,
                           overlaps_wrong_generic=start<0x8bc00000 and start+length>0x8b700000))

overlay_blob = (P.parent/'kernel102/stock-audio-extracted/overlay-0.dtbo').read_bytes()
overlay_nodes = parse(overlay_blob)
overlay_memory = []
for path, props in overlay_nodes.items():
    if 'reserved' in path or 'camera_region' in path or any(b'pil_camera_mem' in v for v in props.values()):
        overlay_memory.append(dict(path=path, properties={k:v.hex() for k,v in props.items()}))
(P/'board-memory-artifacts-private.json').write_text(json.dumps(dict(
    mainline_reserved_ranges=ranges, stock_overlay_memory=overlay_memory), indent=2)+'\n')
report = dict(stage=356, source_commit=commit, source_path=name,
    source_sha256=hashlib.sha256(raw).hexdigest(), exact_board_source_camera_physical=physical,
    exact_board_source_camera_bytes=size, original_source_has_no_map=True,
    wrong_generic_physical=0x8b700000, generic_address_is_not_the_board_camera_region=True,
    mainline_dtb_sha256=hashlib.sha256(blob).hexdigest(),
    mainline_camera_containing_reserved_ranges=[r for r in ranges if r['contains_board_camera']],
    mainline_wrong_generic_containing_ranges=[r for r in ranges if r['overlaps_wrong_generic']],
    stock_overlay_sha256=hashlib.sha256(overlay_blob).hexdigest(),
    stock_overlay_memory_nodes_count=len(overlay_memory),
    physical_cpu_access_not_proven=True, firmware_boot_not_proven=True, phone_changed=False)
(HERE/'board-memory-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
