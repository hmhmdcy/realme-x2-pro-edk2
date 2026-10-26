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
assert os.geteuid() == 0
assert json.loads((ref / 'usb-source-static-validation.json').read_text())['host_scenarios'] == 289
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(ref / 'ensure-build-volume.py'))
base = Path('/home/cy122/pmos-samurai-kernel118/power132')
stage = Path('/home/cy122/pmos-samurai-build134/usb134')
assert not stage.exists() and shutil.disk_usage(stage.parent).free > 6 * 1024**3
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
build = json.loads((r / 'reference/kernel132/kernel-build-validation.json').read_text())
expected_image = next(a['sha256'] for a in build['artifacts'] if a['role'] == 'Image')
assert sha(base / 'kernel/arch/arm64/boot/Image') == expected_image
baseline = subprocess.check_output(['git', '-C', str(base / 'kernel'), 'diff', '--binary'])
(out / 'baseline132-source-diff-private.patch').write_bytes(baseline)
stage.mkdir(mode=0o700)
for name in ['kernel', 'initramfs']:
    subprocess.run(['cp', '-a', str(base / name), str(stage / name)], check=True, timeout=300)
    print('K134_ISOLATED_SOURCE_COPY', name, flush=True)
k = stage / 'kernel'
assert subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']) == baseline
config = k / '.config'
body = config.read_text()
assert body.count('CONFIG_LOCALVERSION="-rmx1931-samurai-k132"') == 1 and body.count(str(base / 'initramfs')) == 1
config.write_text(body.replace('CONFIG_LOCALVERSION="-rmx1931-samurai-k132"', 'CONFIG_LOCALVERSION="-rmx1931-samurai-k134"')
    .replace(str(base / 'initramfs'), str(stage / 'initramfs')) + '\nCONFIG_USB_INPUT_SAMURAI=y\n')
for name in ['samurai-usb-input.c', 'samurai-usb-input-decode.h']:
    assert not (k / 'drivers/power/supply' / name).exists()
    shutil.copy2(ref / name, k / 'drivers/power/supply' / name)
changes = {}
makefile = Path('drivers/power/supply/Makefile')
old = (k / makefile).read_text()
new = old + '\nobj-$(CONFIG_USB_INPUT_SAMURAI) += samurai-usb-input.o\n'
(k / makefile).write_text(new)
changes[str(makefile)] = (old, new)
kconfig = Path('drivers/power/supply/Kconfig')
old = (k / kconfig).read_text()
option = '''config USB_INPUT_SAMURAI
\tbool "Realme X2 Pro USB power input status monitor"
\tdepends on OF && MFD_SPMI_PMIC && POWER_SUPPLY
\thelp
\t  Read PM8150B USBIN and Type-C source status on RMX1931. Expose
\t  BC1.2 or Type-C advertised current through a read-only power supply.
\t  This does not configure charging, negotiate PD, or change USB roles.

'''
pos = old.rindex('endif # POWER_SUPPLY')
new = old[:pos] + option + old[pos:]
(k / kconfig).write_text(new)
changes[str(kconfig)] = (old, new)
board = Path('arch/arm64/boot/dts/qcom/sm8150-samurai.dts')
old = (k / board).read_text()
new = old.replace('/* Stock QUP1 wiring; no charger client or charging policy is bound. */',
                  '/* Stock QUP1 wiring; MP2650 provides read-only charging observation. */')
new += '''
/* OEM PM8150B USBIN / Type-C status; no charging or PD control writes. */
&spmi_bus {
\tpmic@2 {
\t\tusb-input@1300 {
\t\t\tcompatible = "realme,rmx1931-usb-input";
\t\t\treg = <0x1300>;
\t\t};
\t};
};
'''
(k / board).write_text(new)
changes[str(board)] = (old, new)
binding = Path('Documentation/devicetree/bindings/power/supply/realme,rmx1931-usb-input.yaml')
assert not (k / binding).exists()
shutil.copy2(ref / binding.name, k / binding)
patch = ''.join(''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
    fromfile='a/' + name, tofile='b/' + name)) for name, (a, b) in changes.items())
(ref / 'usb-input-integration.patch').write_text(patch)
assert sha(base / 'kernel/arch/arm64/boot/Image') == expected_image
assert subprocess.check_output(['git', '-C', str(base / 'kernel'), 'diff', '--binary']) == baseline
assert sha(k / 'drivers/power/supply/mp2650_charger.c') == 'de2659f66e30f4d30a7790de844702da09bb417a469d7a0fe586700ed2670b02'
report = dict(candidate=134, isolated_private_e_source_copy=True, base132_source_and_image_preserved=True,
    in_tree_builtin_usb_input_monitor=True, existing_mp2650_driver_unchanged=True,
    only_new_pmic_usb_input_node_planned=True, usb_role_or_charging_writes=0,
    source_driver_sha256=sha(k / 'drivers/power/supply/samurai-usb-input.c'),
    source_decoder_sha256=sha(k / 'drivers/power/supply/samurai-usb-input-decode.h'),
    full_build_pending=True, deployed=False, charging_control_accepted=False, goal_complete=False)
(ref / 'source-integration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_BUILTIN_USB_INPUT_SOURCE_INTEGRATED_BASE132_PRESERVED', flush=True)
