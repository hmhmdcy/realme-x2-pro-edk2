"""Build only the embedded lab FDT; restore firmware outputs and all source."""
from pathlib import Path
import importlib.util
import json

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
repo = Path('/home/cy122/edk2-samurai/repo')
proof = json.loads((R / 'board-build-validation.json').read_text())
dt = dict(candidate_dtb_sha256=proof['dtb_sha256'], **proof['semantic_delta'])
(P / 'boot-dtb-input-private.json').write_text(json.dumps(dt, indent=2) + '\n')
text = (R.parent / 'kernel219/build-package.py').read_text()
changes = [
    ("out = Path('/mnt/e/edk2-samurai-out/kernel219')", "out = Path('/mnt/e/edk2-samurai-out/kernel235')"),
    ("(ref / 'mode-dtb-validation.json')", "(out / 'boot-dtb-input-private.json')"),
    ("out / 'candidate-build/factory-modes.dtb'", "out / 'board-build-r2/imx319-p-lab.dtb'"),
    ("out / 'candidate-build/factory-modes.yaml'", "out / 'board-build-r2/imx319-p-lab.yaml'"),
    ('kernel211/boot-partition-k211-sensor-domain.img', 'kernel232/boot-partition-k232-pmic-identity.img'),
    ('c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6',
     '45f398f26def1688cdbb35c1ed5bc9b80ec35fa1744fcee3f9ca0fa6cff339df'),
    ('assert len(dt_changes) == 1', 'assert len(dt_changes) == 3'),
    ("boot-partition-k219-front-modes.img'\nassert not boot_path", "boot-partition-k235-imx319-p-lab.img'\nassert not boot_path"),
    ('report = dict(stage=219,', 'report = dict(stage=235,'),
    ('new_camera_nodes=', 'new_imx319_lab_nodes='),
    ('82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58',
     'fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'),
]
for old, new in changes:
    assert text.count(old) == 1, (old, text.count(old))
    text = text.replace(old, new, 1)
compile(text, 'boot-builder235', 'exec')
(P / 'generated-boot-builder-private.py').write_text(text)
fv = repo / 'workspace/Build/samurai/RELEASE_GCC5/FV'
outputs = [repo / 'boot-samurai.img', fv / 'SM8150_UEFI.fd', fv / 'FVMAIN.Fv']
backup = P / 'firmware-outputs-before'
backup.mkdir(mode=0o700)
saved = {str(path): path.read_bytes() for path in outputs}
for path in outputs:
    (backup / path.name).write_bytes(saved[str(path)])
spec = importlib.util.spec_from_file_location('fdt235', R.parent / 'kernel211/fdt_compare.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
try:
    exec(compile(text, 'boot-builder235', 'exec'), dict(__file__=str(R / 'build-package-generated.py'), fdt_compare_function=f.compare))
finally:
    for path in outputs:
        path.write_bytes(saved[str(path)])
    assert all(path.read_bytes() == saved[str(path)] for path in outputs)
    (P / 'firmware-output-restoration-private.json').write_text(json.dumps(dict(all_three_generated_outputs_restored=True), indent=2) + '\n')
report = json.loads((R / 'build-package-validation.json').read_text())
report.update(firmware_generated_outputs_restored=True, experimental_imx319_l1_l4_only=True,
              required_module_parameter='qcom_pm8008.experimental_p_imx319_power=1',
              runtime_not_accepted=True, phone_unchanged=True)
for directory in [R, P]:
    (directory / 'build-package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(stage=235, boot_candidate_built=True, firmware_code_preserved=True, phone_unchanged=True)))
