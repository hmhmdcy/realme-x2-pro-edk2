from pathlib import Path
import difflib
import hashlib
import json
import os
import runpy
import shutil
import subprocess
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
assert not (ref / 'source-integration-validation.json').exists()
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(ref / 'ensure-build-volume.py'))
base = Path('/home/cy122/pmos-samurai-kernel118/power132')
stage = Path('/home/cy122/pmos-samurai-build134/usb134')
k = stage / 'kernel'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected_image = next(a['sha256'] for a in json.loads((r / 'reference/kernel132/kernel-build-validation.json').read_text())['artifacts'] if a['role'] == 'Image')
baseline = (out / 'baseline132-source-diff-private.patch').read_bytes()
assert sha(base / 'kernel/arch/arm64/boot/Image') == expected_image
assert (k / '.config').read_text().count('CONFIG_USB_INPUT_SAMURAI=y') == 1
assert (k / 'drivers/power/supply/Kconfig').read_bytes() == (base / 'kernel/drivers/power/supply/Kconfig').read_bytes()
assert (k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes() == (base / 'kernel/arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes()
assert not (k / 'Documentation/devicetree/bindings/power/supply/realme,rmx1931-usb-input.yaml').exists()
name = 'drivers/power/supply/Makefile'
changes = {name: ((base / 'kernel' / name).read_text(), (k / name).read_text())}
assert changes[name][1].count('CONFIG_USB_INPUT_SAMURAI') == 1
source = (ref / 'prepare-usb-source.py').read_text()
source = source[source.index("kconfig = Path('drivers/power/supply/Kconfig')"):]
exec(compile(source, 'resume-only-unfinished-kconfig-dt-integration', 'exec'))
(out / 'source-prepare-r1-failure-private.txt').write_text('Initial source preparation used an endmenu anchor, but this Kconfig ends with endif # POWER_SUPPLY. Copy/config/Makefile completed; no Kconfig, board or binding mutation occurred before failure. Resume completed only unfinished integration.\n')
print('K134_SOURCE_PREPARATION_RESUMED_WITHOUT_REPLAYING_COPY', flush=True)
