"""Finish metadata audit after successful targeted build removed modules.order."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077)
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
private=Path('/mnt/e/edk2-samurai-out/kernel210');out=private/'modules';baseline=private/'source-before'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (here/'camera-module-build-validation.json').exists()
assert not (k/'modules.order').exists()
assert (out/'generated-Module.symvers-private').read_bytes()==(k/'Module.symvers').read_bytes()
assert (out/'config-camera-private').read_bytes()==(k/'.config').read_bytes()
original_config=(baseline/'.config').read_text();config=(k/'.config').read_text()
delta=set(config.splitlines())^set(original_config.splitlines())
base_symbols=(baseline/'Module.symvers').read_text();base_order=(baseline/'modules.order').read_text()
targets=['drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko','drivers/mfd/qcom-pm8008.ko']
preserve=json.loads((baseline/'build-artifacts-private.json').read_text())
preserve={n:preserve[n] for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']}
sources=json.loads((baseline/'source-file-hashes-private.json').read_text())
for n in ['drivers/media/i2c/imx471.c','drivers/mfd/qcom-pm8008.c']:
    assert sha(k/n)==sources[n];preserve[n]=sources[n]
source=(here/'build-camera-modules.py').read_text();suffix=source.split("# A partial target build may write only its target exports.",1)[1]
exec(compile('# A partial target build may write only its target exports.'+suffix,'finish-verified-module-build','exec'))
report=json.loads((here/'camera-module-build-validation.json').read_text());report.update(first_config_audit_stopped_for_two_additional_disabled_test_helpers=True,targeted_build_removed_modules_order=True,modules_order_restored_from_baseline_plus_two_new_modules=True)
(here/'camera-module-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
