"""Adapt audited 214 validators to a separate complete r6 output tree."""
from pathlib import Path
here=Path(__file__).resolve().parent;prior=here.parent/'kernel214'
for old,new in [('inspect-full-features.py','inspect-full-features.py'),('collect-forward-packages.py','collect-forward-packages.py'),('host-runtime-qa.py','host-runtime-qa.py')]:
    code=(prior/old).read_text()
    code=code.replace('stage=214','stage=219').replace("/mnt/e/edk2-samurai-out/kernel214'","/mnt/e/edk2-samurai-out/kernel219'")
    code=code.replace("root/'work/libcamera/src/", "root/'work/libcamera219/src/")
    code=code.replace('/work/libcamera/src/','/work/libcamera219/src/')
    code=code.replace('libcamera214-qa-prefix','libcamera219-qa-prefix')
    code=code.replace("root/'packages'","root/'packages219'").replace("root/'packages-config'","root/'packages-config219'")
    code=code.replace("keys=private/'phone-trusted-public-keys'","keys=private.parent/'kernel214/phone-trusted-public-keys'")
    code=code.replace("assert json.loads((here/'full-libcamera-build-validation.json').read_text())['abuild_exit']==0", "assert json.loads((here/'r6-package-build-validation.json').read_text())['framework_and_device_config_packages_built']")
    code=code.replace("'0.1.0-r0'", "'0.1.0-r1'").replace("'99990.7.2-r5'", "'99990.7.2-r6'")
    code=code.replace("repo/'linux-port/camera/configuration.yaml'", "root/'work/samurai-camera-config219/configuration.yaml'")
    code=code.replace("root/'candidate'", "root/'candidate219'").replace('/candidate/', '/candidate219/')
    code=code.replace('k214-runtime', 'k219-runtime').replace('camera214 full','camera219 full')
    compile(code,new,'exec');(here/new).write_text(code)
print('Separate r6 feature, signature, payload and emulated runtime validators prepared')
