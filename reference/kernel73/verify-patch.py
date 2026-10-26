from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

root = Path('/mnt/e/RealmeX2Pro edk2')
reference = root/'reference/kernel73'
kernel = Path('/home/cy122/x2pro-linux/linux')
patch = root/'linux-port/patches/0009-drm-panel-samsung-sofef03f-native-display.patch'
paths = {
    'arch/arm64/boot/dts/qcom/sm8150-samurai.dts':'dts-before',
    'drivers/gpu/drm/panel/Kconfig':'panel-kconfig-before',
    'drivers/gpu/drm/panel/Makefile':'panel-makefile-before',
    'drivers/gpu/drm/panel/panel-samsung-sofef03f.c':None,
    'Documentation/devicetree/bindings/display/panel/samsung,sofef03f-m.yaml':None,
}
with tempfile.TemporaryDirectory(prefix='k73-patch-',dir='/home/cy122/x2pro-linux') as directory:
    work = Path(directory)
    for name, before in paths.items():
        target = work/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if before:
            shutil.copyfile(reference/before,target)
    subprocess.run(['git','apply','--check',str(patch)],cwd=work,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=work,check=True)
    for name in paths:
        assert (work/name).read_bytes() == (kernel/name).read_bytes(), name
result = dict(patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
    check_pass=True,applied_files_match_actual_source=True,paths=list(paths))
(reference/'patch-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
