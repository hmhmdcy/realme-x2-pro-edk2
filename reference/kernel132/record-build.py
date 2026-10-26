#!/usr/bin/env python3
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
ref = r / 'reference/kernel132'
out = Path('/mnt/e/edk2-samurai-out/kernel132')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
stage = Path('/home/cy122/pmos-samurai-kernel118/power132')
k = stage / 'kernel'
base = Path('/home/cy122/pmos-samurai-kernel129/kernel')
release = (k / 'include/config/kernel.release').read_text().strip()
assert release == '7.3.0-rc6-rmx1931-samurai-k132+'
assert (out / 'depmod-private.txt').stat().st_size == 0
assert json.loads((ref / 'power-schema-validation.json').read_text())['all_existing_nodes_and_property_bytes_unchanged']
for name in ['modules-build-private.log', 'image-build-private.log']:
    assert 'error:' not in (out / name).read_text().lower()
banner = [l for l in subprocess.check_output(['strings', str(k / 'vmlinux')], text=True).splitlines() if l.startswith('Linux version 7.')]
assert banner and all(release in l and '#132 SMP' in l for l in banner)
driver = Path('drivers/power/supply/mp2650_charger.c')
assert (k / driver).read_bytes() == (base / driver).read_bytes()
old_config = (base / '.config').read_text()
expected_config = old_config.replace('-rmx1931-samurai-k129', '-rmx1931-samurai-k132').replace(str(base.parent / 'initramfs'), str(stage / 'initramfs'))
assert (k / '.config').read_text() == expected_config
board = Path('arch/arm64/boot/dts/qcom/sm8150-samurai.dts')
old_diff = subprocess.check_output(['git', 'diff', '--binary'], cwd=base)
assert old_diff == (out / 'baseline129-source-diff-private.patch').read_bytes()
for changed in subprocess.check_output(['git', 'diff', '--name-only'], cwd=k, text=True).splitlines():
    if changed != str(board):
        assert (k / changed).read_bytes() == (base / changed).read_bytes(), changed

code = (r / 'reference/kernel126/record-build-and-modules.py').read_text()
node = next(n for n in ast.parse(code).body if isinstance(n, ast.FunctionDef) and n.name == 'executable_sections')
scope = {'struct': struct}
exec(ast.get_source_segment(code, node), scope)
sections = scope['executable_sections']
def modules(path):
    result = {}
    with tarfile.open(path) as tf:
        for m in tf:
            assert (m.isfile() or m.isdir()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
            if m.isfile() and m.name.endswith('.ko'):
                name = m.name.split('/kernel/', 1)[1]
                assert name not in result
                result[name] = tf.extractfile(m).read()
    return result
old = modules(out.parent / 'kernel129/modules-k129-private.tar.gz')
new = modules(out / 'modules-k132-private.tar.gz')
assert old.keys() == new.keys() and len(new) == 770
assert all(sections(old[name]) == sections(new[name]) for name in new)
for data in new.values():
    start = data.index(b'vermagic=') + 9
    assert data[start:data.index(0, start)].decode().startswith(release + ' ')
sys.path.insert(0, str(r / 'reference/kernel129'))
from cpio_contract import members, console_ok
oldcpio = members(base / 'usr/initramfs_data.cpio')
newcpio = members(k / 'usr/initramfs_data.cpio')
assert console_ok(oldcpio) and console_ok(newcpio) and set(oldcpio) == set(newcpio)
changedcpio = [name for name in oldcpio if oldcpio[name] != newcpio[name]]
assert set(changedcpio) == {'lib/modules/samurai/' + name + '.ko' for name in ['btbcm', 'btqca', 'hci_uart']}
for name in ['btbcm', 'btqca', 'hci_uart']:
    data = new['drivers/bluetooth/' + name + '.ko']
    assert newcpio['lib/modules/samurai/' + name + '.ko']['sha256'] == hashlib.sha256(data).hexdigest()
    assert (stage / ('initramfs/lib/modules/samurai/' + name + '.ko')).read_bytes() == data
artifacts = []
for role, path in [('Image', k / 'arch/arm64/boot/Image'), ('DTB', k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')]:
    payload = path.read_bytes()
    target = out / (role + '-k132-private')
    assert not target.exists()
    target.write_bytes(payload)
    artifacts.append(dict(role=role, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()))
pack = out / 'modules-k132-private.tar.gz'
report = dict(candidate=132, release=release, full_image_modules_dtb_build_pass=True,
              full_banner_matches=True, module_count=770,
              all_770_module_executable_sections_byte_equal129=True,
              all_module_vermagic_matches=True, matching_initramfs_bt_modules=True,
              encoded_console_char_5_1_uid_gid_zero_mode0600=True,
              existing_initramfs_members_preserved_except_matching_bt_vermagic=True,
              baseline129_source_and_image_preserved=True, charger_driver_unchanged=True,
              dtb_only_one_charger_node_added=True, embedded_uefi_dtb_rebuild_required=True,
              archive_sha256=hashlib.sha256(pack.read_bytes()).hexdigest(), archive_bytes=pack.stat().st_size,
              artifacts=artifacts, depmod_system_map_no_diagnostics=True, not_deployed=True,
              charging_control_accepted=False, goal_complete=False)
for folder, filename in [(ref, 'kernel-build-validation.json'), (out, 'candidate-package-validation.json')]:
    (folder / filename).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
