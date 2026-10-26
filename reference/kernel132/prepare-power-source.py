#!/usr/bin/env python3
from pathlib import Path
import difflib
import hashlib
import json
import os
import runpy
import shutil
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
base = Path('/home/cy122/pmos-samurai-kernel129')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
stage = Path('/home/cy122/pmos-samurai-kernel118/power132')
assert os.geteuid() == 0 and not stage.exists()
assert shutil.disk_usage(stage.parent).free > 6 * 1024**3
assert shutil.disk_usage('/mnt/e').free > 12 * 1024**3
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
base_build = json.loads((r / 'reference/kernel129/kernel-build-validation.json').read_text())
expected = next(a['sha256'] for a in base_build['artifacts'] if a['role'] == 'Image')
assert sha(base / 'kernel/arch/arm64/boot/Image') == expected
driver = Path('drivers/power/supply/mp2650_charger.c')
assert sha(base / 'kernel' / driver) == 'de2659f66e30f4d30a7790de844702da09bb417a469d7a0fe586700ed2670b02'
out.mkdir(mode=0o700)
baseline_diff = subprocess.check_output(['git', '-C', str(base / 'kernel'), 'diff', '--binary'])
(out / 'baseline129-source-diff-private.patch').write_bytes(baseline_diff)
stage.mkdir(mode=0o700)
for name in ['kernel', 'initramfs']:
    subprocess.run(['cp', '-a', str(base / name), str(stage / name)], check=True, timeout=300)
    print('POWER132_ISOLATED_E_COPY', name, flush=True)
assert subprocess.check_output(['git', '-C', str(stage / 'kernel'), 'diff', '--binary']) == baseline_diff
config = stage / 'kernel/.config'
body = config.read_text()
assert body.count('CONFIG_LOCALVERSION="-rmx1931-samurai-k129"') == 1
assert body.count(str(base / 'initramfs')) == 1
config.write_text(body.replace('CONFIG_LOCALVERSION="-rmx1931-samurai-k129"', 'CONFIG_LOCALVERSION="-rmx1931-samurai-k132"').replace(str(base / 'initramfs'), str(stage / 'initramfs')))
board = Path('arch/arm64/boot/dts/qcom/sm8150-samurai.dts')
old = (base / 'kernel' / board).read_text()
anchor = '&i2c1 {\n\tclock-frequency = <400000>;\n\tstatus = "okay";\n};'
replacement = '''&i2c1 {
\tclock-frequency = <400000>;
\tstatus = "okay";

\t/* QUP1 / 0x5c, verified MP2650: read-only power_supply observation. */
\tcharger@5c {
\t\tcompatible = "mps,mp2650";
\t\treg = <0x5c>;
\t};
};'''
assert old.count(anchor) == 1
new = old.replace(anchor, replacement)
(stage / 'kernel' / board).write_text(new)
(ref / 'mp2650-persistent-node.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/' + str(board), tofile='b/' + str(board))))
binding = stage / 'kernel/Documentation/devicetree/bindings/power/supply/mps,mp2650.yaml'
assert not binding.exists()
shutil.copy2(ref / 'mps,mp2650.yaml', binding)
assert sha(base / 'kernel/arch/arm64/boot/Image') == expected
assert subprocess.check_output(['git', '-C', str(base / 'kernel'), 'diff', '--binary']) == baseline_diff
assert sha(stage / 'kernel' / driver) == sha(base / 'kernel' / driver)
report = dict(candidate=132, isolated_build_on_existing_e118_volume=True,
              base129_image_and_driver_source_preserved=True, driver_unchanged=True,
              added_node='QUP1 charger@5c', bus_clock_unchanged=400000,
              new_binding_sha256=sha(binding), full_build_pending=True,
              actual_deployment_pending=True, charging_control_accepted=False)
(ref / 'source-static-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
