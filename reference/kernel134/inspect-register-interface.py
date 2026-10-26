from pathlib import Path
import hashlib
import json
import runpy
r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel134')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
k = Path('/home/cy122/pmos-samurai-kernel118/power132/kernel')
files = ['drivers/base/regmap/regmap-debugfs.c', 'drivers/base/regmap/regmap-spmi.c',
         'drivers/mfd/qcom-spmi-pmic.c', 'drivers/usb/typec/tcpm/tcpm.c',
         'Documentation/devicetree/bindings/usb/qcom,pmic-typec.yaml']
report = {}
for name in files:
    data = (k / name).read_bytes()
    target = out / ('current132--' + name.replace('/', '--'))
    assert not target.exists()
    target.write_bytes(data)
    report[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
(r / 'reference/kernel134/register-interface-source-validation.json').write_text(json.dumps(dict(
    stage=134, sources=report, source_mutations=0, phone_register_reads=0, goal_complete=False), indent=2) + '\n')
print('K134_CURRENT_SOURCE_INTERFACES_COPIED_NO_MUTATIONS', flush=True)
