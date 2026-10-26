"""Reuse the audited firmware packer with boot235 as the exact rollback image."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel267')
repo=Path('/home/cy122/edk2-samurai/repo')
proof=json.loads((R/'board-build-validation.json').read_text())
assert proof['unrelated_properties_unchanged']
dt=dict(candidate_dtb_sha256=proof['dtb_sha256'],**proof['semantic_delta'])
(P/'boot-dtb-input-private.json').write_text(json.dumps(dt,indent=2)+'\n')
oldproof=json.loads((R.parent/'kernel235/build-package-validation.json').read_text())
old=P.parent/'kernel235/boot-partition-k235-imx319-p-lab.img'
assert hashlib.sha256(old.read_bytes()).hexdigest()==oldproof['boot_sha256']
text=(R.parent/'kernel219/build-package.py').read_text()
retry=sys.argv[1:]==['--pin-original-firmware-version']
assert not sys.argv[1:] or retry
if retry:
    delta=json.loads((P/'rejected-firmware-delta-private.json').read_text())
    versions=[]
    for row in delta:
        if not row['name']:continue
        assert row['name'] in ['PlatformSmbiosDxe','BdsDxe','UiApp']
        body=(P/'firmware-delta-r2'/(row['guid']+'-old.bin')).read_bytes()
        newer=(P/'firmware-delta-r2'/(row['guid']+'-new.bin')).read_bytes()
        offset=row['difference_spans'][0]['start']
        oldver=body[offset:offset+14].decode('utf-16-le')
        newver=newer[offset:offset+14].decode('utf-16-le')
        assert re.fullmatch('[0-9a-f]{7}',oldver) and re.fullmatch('[0-9a-f]{7}',newver)
        assert newer.replace(newver.encode('utf-16-le'),oldver.encode('utf-16-le'))==body
        versions.append(oldver)
    assert len(versions)==3 and len(set(versions))==1
    tools=P/'firmware-tools';tools.mkdir(mode=0o700)
    shim=tools/'git'
    shim.write_text('#!/bin/sh\nif [ "$#" = 3 ] && [ "$1" = describe ] && [ "$2" = --tags ] && [ "$3" = --always ]; then\n  printf "%s\\n" '+versions[0]+'\nelse\n  exec /usr/bin/git "$@"\nfi\n')
    shim.chmod(0o700)
    text=text.replace("target = out / 'firmware'","target = out / 'firmware-r2'")
    text=text.replace("env.update(PATH='/home/cy122/.local/bin:' + env['PATH']", "env.update(PATH=str(out / 'firmware-tools') + ':/home/cy122/.local/bin:' + env['PATH']")
    (R/'firmware-version-validation.json').write_text(json.dumps(dict(stage=267,rejected_first_build=True,
      three_non_camera_modules_differ_only_in_git_version=True,firmware_version_pinned_to_existing_boot=True,
      no_firmware_source_or_git_checkout_modified=True),indent=2)+'\n')
changes=[
 ("out = Path('/mnt/e/edk2-samurai-out/kernel219')","out = Path('/mnt/e/edk2-samurai-out/kernel267')"),
 ("(ref / 'mode-dtb-validation.json')","(out / 'boot-dtb-input-private.json')"),
 ("out / 'candidate-build/factory-modes.dtb'","out / 'board-build-r1/sm8150-samurai.dtb'"),
 ("out / 'candidate-build/factory-modes.yaml'","out / 'board-build-r1/sm8150-samurai.yaml'"),
 ('kernel211/boot-partition-k211-sensor-domain.img','kernel235/boot-partition-k235-imx319-p-lab.img'),
 ('c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6',oldproof['boot_sha256']),
 ("assert semantic['only_old_nodes'] == []","assert semantic['only_old_nodes'] == dt['only_old_nodes']"),
 ('assert len(dt_changes) == 1','assert len(dt_changes) == 8'),
 ("boot-partition-k219-front-modes.img'\nassert not boot_path","boot-partition-k267-common-camera.img'\nassert not boot_path"),
 ('report = dict(stage=219,','report = dict(stage=267,'),
 ('82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58','ff9fdfa346249d836c0f830c9ea2480b6b06b280089007a054a6d2a0514f5822')]
for a,b in changes:
    assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b,1)
(P/'generated-boot-builder-private.py').write_text(text)
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV'
outputs=[repo/'boot-samurai.img',fv/'SM8150_UEFI.fd',fv/'FVMAIN.Fv']
saved={str(p):p.read_bytes() for p in outputs}
backup=P/('firmware-outputs-before-r2' if retry else 'firmware-outputs-before');backup.mkdir(mode=0o700)
for p in outputs:(backup/p.name).write_bytes(saved[str(p)])
spec=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
try:
    exec(compile(text,'boot-builder267','exec'),dict(__file__=str(R/'build-package-generated.py'),fdt_compare_function=f.compare))
finally:
    for p in outputs:p.write_bytes(saved[str(p)])
    assert all(p.read_bytes()==saved[str(p)] for p in outputs)
    (P/'firmware-output-restoration-private.json').write_text(json.dumps(dict(all_three_generated_outputs_restored=True))+'\n')
report=json.loads((R/'build-package-validation.json').read_text())
report.update(firmware_generated_outputs_restored=True,standard_pmic_sensor_candidates=True,
              old_lab_parameters_not_required=True,runtime_not_accepted=True,phone_unchanged=True)
for directory in [R,P]:(directory/'build-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=267,boot_candidate_built=True,firmware_code_preserved=True,phone_unchanged=True)))
