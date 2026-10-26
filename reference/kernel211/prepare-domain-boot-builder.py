from pathlib import Path
import ast
here=Path(__file__).resolve().parent
source=(here.parent/'kernel210/build-package.py').read_text().replace("out = Path('/mnt/e/edk2-samurai-out/kernel210')","out = Path('/mnt/e/edk2-samurai-out/kernel211')")
source=source.replace("'camera-dtb-validation.json'","'sensor-domain-dtb-validation.json'").replace("'camera-dtb-r2/camera.dtb'","'sensor-domain-dtb/sensor-domain.dtb'").replace("'camera-dtb-r2/camera.yaml'","'sensor-domain-dtb/sensor-domain.yaml'")
source=source.replace("'kernel204/boot-partition-k204-bt-wake.img'","'kernel210/boot-partition-k210-front.img'").replace('cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082','89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0')
source=source.replace("assert len(dt_changes) == 2","assert len(dt_changes) == 1").replace("'boot-partition-k210-front.img'","'boot-partition-k211-sensor-domain.img'").replace('report = dict(stage=210,','report = dict(stage=211,')
assert "before = (out.parent / 'kernel210/boot-partition-k210-front.img')" in source
ast.parse(source);(here/'build-package.py').write_text(source)
print('211 boot builder uses deployed210 rollback and accepts only one sensor-domain property change.')
