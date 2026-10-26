"""Retire the uninstalled board-location fallback and prepare a new build."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel266')
archive = P / 'orientation-fallback-rejected'
archive.mkdir(mode=0o700)
for name in ['imx319.c', 'imx319-standard-metadata.patch', 'source-validation.json',
             'imx319-build-validation.json']:
    shutil.copyfile(R / name, archive / name)
shutil.copyfile(R / 'imx319-build-validation.json', R / 'imx319-build-r2-validation.json')
for name in ['prepare-driver.py', 'fix-style.py', 'check-geometry-source.py']:
    subprocess.run([sys.executable, str(R / name)], check=True)
source = (R / 'imx319.c').read_text()
assert 'default_orientation' not in source
assert 'V4L2_FWNODE_ORIENTATION_BACK' not in source
assert 'orientation = <1>;' in (R / 'imx319-p-lab.dtsi').read_text()
code = (R / 'build-imx319-r2.py').read_text().replace(
    "out = P / 'imx319-build-r2'", "out = P / 'imx319-build-r3'").replace(
    "'kernel-before-r2-private.json'", "'kernel-before-r3-private.json'")
(R / 'build-imx319-r3.py').write_text(code)
report = dict(stage=266, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              orientation_from_device_tree_only=True, board_orientation_fallback_removed=True,
              historical_r2_receipt_preserved=True, candidate_not_installed=True,
              existing_lab_power_and_mode_profiles_still_require_cleanup=True)
(R / 'device-tree-alignment-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
