"""Lock exact built artifacts and current rollback; do not operate the phone."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
pmic = json.loads((R / 'pmic-build-validation.json').read_text())
sensor = json.loads((R / 'imx319-build-validation.json').read_text())
boot = json.loads((R / 'build-package-validation.json').read_text())
for report in [pmic, sensor]:
    for name, digest in report['source_inputs'].items():
        assert sha(R / name) == digest
assert json.loads((R / 'imx319-fault-validation.json').read_text())['source_sha256'] == sha(R / 'imx319.c')
assert json.loads((R / 'lab-fault-validation.json').read_text())['source_sha256'] == sha(R / 'qcom-pm8008-imx319-lab.c')
paths = {
    'mfd_module': P / 'pmic-build-r4/qcom-pm8008.ko',
    'lab_module': P / 'pmic-build-r4/qcom-pm8008-imx319-lab.ko',
    'sensor_module': P / 'imx319-build-r4/imx319.ko',
    'provider_module': P.parent / 'kernel232/intree-build/reset-realme-rmx1931-pm8008.ko',
    'boot_candidate': P / 'boot-partition-k235-imx319-p-lab.img',
    'boot232_rollback': P.parent / 'kernel232/boot-partition-k232-pmic-identity.img',
    'boot219_rollback': P.parent / 'kernel219/boot-partition-k219-front-modes.img',
}
# Provider is retained, not installed again. Locate its already locked artifact.
previous = json.loads((P.parent / 'kernel233/deployment-lock-private.json').read_text())
paths['provider_module'] = Path(previous['files']['provider_module']['path'])
files = {name: dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size) for name, path in paths.items()}
assert files['mfd_module']['sha256'] == pmic['modules']['qcom-pm8008']['sha256']
assert files['lab_module']['sha256'] == pmic['modules']['qcom-pm8008-imx319-lab']['sha256']
assert files['sensor_module']['sha256'] == sensor['sha256']
assert files['provider_module']['sha256'] == '2223f33725a03fc0ddb7f6a33e4b507d5b6952e3edf49ec401e1627d53b59e80'
assert files['boot_candidate']['sha256'] == boot['boot_sha256']
assert files['boot232_rollback']['sha256'] == boot['rollback_boot_sha256']
lock = dict(stage=235, files=files, runtime_before_guard='/var/lib/samurai/k233-runtime/boot-id-private.txt',
            module_parameter='experimental_p_imx319_power=1', only_boot_may_be_flashed=True,
            current232_mfd_must_remain_live_until_reboot=True, hardware_not_yet_accepted=True)
path = P / 'deployment-lock-private.json'
assert not path.exists()
path.write_text(json.dumps(lock, indent=2) + '\n')
print(json.dumps(dict(stage=235, locked_artifacts=len(files), no_phone_operation=True)))
