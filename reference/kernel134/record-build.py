from pathlib import Path
import ast
import hashlib
import json
import runpy
import struct
import subprocess
import sys
import tarfile
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(ref / 'ensure-build-volume.py'))
stage = Path('/home/cy122/pmos-samurai-build134/usb134')
k = stage / 'kernel'
base = Path('/home/cy122/pmos-samurai-kernel118/power132/kernel')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
release = (k / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k134+'
assert (out / 'depmod-private.txt').stat().st_size == 0
assert json.loads((ref / 'usb-schema-validation.json').read_text())['all_existing_nodes_and_property_bytes_unchanged']
for name in ['usb-input-build-r2-private.log', 'modules-build-private.log', 'image-build-private.log']:
    assert 'error:' not in (out / name).read_text().lower()
assert 'warning:' not in (out / 'usb-input-build-r2-private.log').read_text().lower()
banner = [l for l in subprocess.check_output(['strings', str(k / 'vmlinux')], text=True).splitlines() if l.startswith('Linux version 7.')]
assert banner and all(release in l and '#134 SMP' in l for l in banner)
symbols = subprocess.check_output(['aarch64-linux-gnu-nm', str(k / 'vmlinux')], text=True)
assert ' samurai_usb_probe\n' in symbols and ' samurai_usb_driver\n' in symbols
def configuration(path):
    answer = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_'):
            name, value = line.split('=', 1)
            answer[name] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            answer[line[2:-11]] = 'n'
    return answer
oldcfg, newcfg = configuration(base / '.config'), configuration(k / '.config')
expected = oldcfg.copy()
expected['CONFIG_LOCALVERSION'] = '"-rmx1931-samurai-k134"'
expected['CONFIG_INITRAMFS_SOURCE'] = '"' + str(stage / 'initramfs') + '"'
expected['CONFIG_USB_INPUT_SAMURAI'] = 'y'
assert newcfg == expected, [(name, oldcfg.get(name), newcfg.get(name)) for name in set(oldcfg) | set(newcfg) if expected.get(name) != newcfg.get(name)]
assert subprocess.check_output(['git', 'diff', '--binary'], cwd=base) == (out / 'baseline132-source-diff-private.patch').read_bytes()
allowed = {'arch/arm64/boot/dts/qcom/sm8150-samurai.dts', 'drivers/power/supply/Makefile', 'drivers/power/supply/Kconfig'}
for changed in subprocess.check_output(['git', 'diff', '--name-only'], cwd=k, text=True).splitlines():
    if changed not in allowed:
        assert (k / changed).read_bytes() == (base / changed).read_bytes(), changed
assert (k / 'drivers/power/supply/mp2650_charger.c').read_bytes() == (base / 'drivers/power/supply/mp2650_charger.c').read_bytes()
for name in ['samurai-usb-input.c', 'samurai-usb-input-decode.h']:
    assert (k / 'drivers/power/supply' / name).read_bytes() == (ref / name).read_bytes()
code = (r / 'reference/kernel126/record-build-and-modules.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'executable_sections')
scope = {'struct': struct}
exec(ast.get_source_segment(code, node), scope)
sections = scope['executable_sections']
def modules(path):
    answer = {}
    with tarfile.open(path) as tf:
        for m in tf:
            assert (m.isfile() or m.isdir()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
            if m.isfile() and m.name.endswith('.ko'):
                name = m.name.split('/kernel/', 1)[1]
                assert name not in answer
                answer[name] = tf.extractfile(m).read()
    return answer
old = modules(out.parent / 'kernel132/modules-k132-private.tar.gz')
new = modules(out / 'modules-k134-private.tar.gz')
assert old.keys() == new.keys() and len(new) == 770
assert all(sections(old[name]) == sections(new[name]) for name in new)
for data in new.values():
    start = data.index(b'vermagic=') + 9
    assert data[start:data.index(0, start)].decode().startswith(release + ' ')
sys.path.insert(0, str(r / 'reference/kernel129'))
from cpio_contract import members, console_ok
oldcpio, newcpio = members(base / 'usr/initramfs_data.cpio'), members(k / 'usr/initramfs_data.cpio')
assert console_ok(oldcpio) and console_ok(newcpio) and set(oldcpio) == set(newcpio)
assert {name for name in oldcpio if oldcpio[name] != newcpio[name]} == {
    'lib/modules/samurai/' + name + '.ko' for name in ['btbcm', 'btqca', 'hci_uart']}
for name in ['btbcm', 'btqca', 'hci_uart']:
    data = new['drivers/bluetooth/' + name + '.ko']
    assert newcpio['lib/modules/samurai/' + name + '.ko']['sha256'] == hashlib.sha256(data).hexdigest()
artifacts = []
for role, path in [('Image', k / 'arch/arm64/boot/Image'), ('DTB', k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')]:
    target = out / (role + '-k134-private')
    assert not target.exists()
    target.write_bytes(path.read_bytes())
    artifacts.append(dict(role=role, bytes=target.stat().st_size, sha256=sha(target)))
pack = out / 'modules-k134-private.tar.gz'
report = dict(candidate=134, release=release, full_image_modules_dtb_build_pass=True, full_banner_matches=True,
    builtin_usb_monitor_linked=True, usb_monitor_W1_compile_without_warnings=True, module_count=770,
    all_existing_module_executable_sections_equal132=True, all_module_vermagic_matches=True,
    matching_initramfs_bt_modules=True, encoded_console_char_5_1_uid_gid_zero_mode0600=True,
    existing_initramfs_members_preserved_except_matching_bt_vermagic=True,
    baseline132_source_and_image_preserved=True, mp2650_driver_unchanged=True,
    existing_configuration_preserved_except_release_initramfs_and_new_usb_monitor=True,
    only_one_new_usb_input_dtb_node=True, embedded_uefi_dtb_rebuild_required=True,
    archive_sha256=sha(pack), archive_bytes=pack.stat().st_size, artifacts=artifacts,
    depmod_system_map_no_diagnostics=True, deployed=False, charging_control_accepted=False, goal_complete=False)
(ref / 'kernel-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_FULL_KERNEL_AND_770_MODULES_CONTRACT_VERIFIED_NOT_DEPLOYED', flush=True)
