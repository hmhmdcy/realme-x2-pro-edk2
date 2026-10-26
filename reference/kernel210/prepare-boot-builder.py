from pathlib import Path
here=Path(__file__).resolve().parent
source=(here.parent/'kernel204/build-package.py').read_text()
source=source.replace("out = Path('/mnt/e/edk2-samurai-out/kernel204')","out = Path('/mnt/e/edk2-samurai-out/kernel210')")
source=source.replace("dt = json.loads((ref / 'uart-candidate-validation.json').read_text())","dt = json.loads((ref / 'camera-dtb-validation.json').read_text())")
source=source.replace("(out / 'sm8150-samurai-bt-wake-static-private.dtb')","(out / 'camera-dtb-r2/camera.dtb')")
source=source.replace("dt['candidate_dtb_sha256']","dt['candidate_dtb_sha256']")
source=source.replace("(out.parent / 'kernel200/boot-partition-k200-mmcx.img')","(out.parent / 'kernel204/boot-partition-k204-bt-wake.img')")
source=source.replace('5109097b74aafd38838174f31fbff2d8c940977fdc4982658ebe86f671d1e1f0','cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082')
begin=source.index("assert set(oldtree) <= set(newtree)");end=source.index('\ndef normalize(line):',begin)
source=source[:begin]+'''from fdt_compare import compare
semantic = compare(oldtree, newtree, out / 'camera-dtb-r2/camera.yaml')
assert semantic['only_old_nodes'] == []
assert semantic['only_new_nodes'] == dt['only_new_nodes']
assert semantic['remaining_changed_properties'] == dt['remaining_changed_properties']
dt_changes = [(p['path'], p['property']) for p in semantic['remaining_changed_properties']]
assert len(dt_changes) == 2
''' +source[end:]
source=source.replace("'boot-partition-k204-bt-wake.img'","'boot-partition-k210-front.img'")
source=source.replace('report = dict(stage=204,','report = dict(stage=210,')
source=source.replace("new_sleep_nodes=dt['new_sleep_nodes']","new_camera_nodes=dt['only_new_nodes']")
assert 'uart-candidate' not in source and "dt['new_sleep_nodes']" not in source
(here/'build-package.py').write_text(source)
print('210 firmware builder prepared from204 with actual204 rollback and typed-reference camera delta checks.')
