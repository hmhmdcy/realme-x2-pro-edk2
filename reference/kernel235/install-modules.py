"""Atomic disk staging only: retain all current live PMIC and sensor drivers."""
from pathlib import Path
import hashlib
import json
import os
import stat
import struct
import subprocess
import tempfile

os.umask(0o077)
root = Path('/var/lib/samurai')
before = root / 'k235-baseline'
tools = root / 'k235-tools'
out = root / 'k235-module-stage'
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (before / 'boot-id-private.txt').read_bytes() == (root / 'k233-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert not out.exists()
tree = Path('/usr/lib/modules') / os.uname().release
sha = lambda data: hashlib.sha256(data).hexdigest()
def inventory_now():
    return {str(p.relative_to(tree)): sha(p.read_bytes()) for p in tree.rglob('*') if p.is_file()}
inventory = json.loads((before / 'module-tree-private.json').read_text())
assert inventory_now() == inventory
assert len(inventory) == 787 and sum(name.endswith('.ko') for name in inventory) == 773
lock = json.loads((tools / 'deployment-lock-private.json').read_text())
mapping = {
    'kernel/drivers/mfd/qcom-pm8008.ko': ('mfd_module', tools / 'qcom-pm8008.ko'),
    'kernel/drivers/regulator/qcom-pm8008-imx319-lab.ko': ('lab_module', tools / 'qcom-pm8008-imx319-lab.ko'),
    'kernel/drivers/media/i2c/imx319.ko': ('sensor_module', tools / 'imx319.ko'),
}
config = Path('/etc/modprobe.d/samurai-pmic-bringup.conf')
original_config = b'options qcom_pm8008 experimental_p_address_only=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008\n'
assert config.read_bytes() == original_config
old_mfd = tree / 'kernel/drivers/mfd/qcom-pm8008.ko'
assert sha(old_mfd.read_bytes()) == 'f633467fa1edcc27eabbb76f8caee00f7d60d3e2440ebca7bc68138c051ae01a'
assert all((tree / name).exists() == (key == 'mfd_module') for name, (key, _) in mapping.items())
def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    names = data[sections[index][4]:sections[index][4] + sections[index][5]]
    result = [data[s[4]:s[4]+s[5]] for s in sections if names[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(result) == 1
    return result[0]
loaded = {}
for name in ['qcom_pm8008', 'qcom_pm8008_regulator', 'reset_realme_rmx1931_pm8008', 'imx471', 'qcom_camss']:
    loaded[name] = Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes()
assert loaded['qcom_pm8008'] == note(old_mfd.read_bytes())
assert not Path('/sys/module/imx319').exists() and not Path('/sys/module/qcom_pm8008_imx319_lab').exists()
old_vermagic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(old_mfd)], text=True).strip()
for name, (key, candidate) in mapping.items():
    assert sha(candidate.read_bytes()) == lock['files'][key]['sha256']
    assert subprocess.check_output(['modinfo', '-F', 'intree', str(candidate)], text=True).strip() == 'Y'
    assert subprocess.check_output(['modinfo', '-F', 'vermagic', str(candidate)], text=True).strip() == old_vermagic
provider = tree / 'kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko'
assert sha(provider.read_bytes()) == lock['files']['provider_module']['sha256']
assert loaded['reset_realme_rmx1931_pm8008'] == note(provider.read_bytes())
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
backup = out / 'before'
backup.mkdir(mode=0o700)
saved = {}
for name in [n for n in inventory if not n.endswith('.ko')] + ['kernel/drivers/mfd/qcom-pm8008.ko']:
    path = tree / name
    dest = backup / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(path.read_bytes())
    metadata = path.stat()
    saved[name] = dict(mode=stat.S_IMODE(metadata.st_mode), uid=metadata.st_uid, gid=metadata.st_gid)
(out / 'saved-file-metadata-private.json').write_text(json.dumps(saved, indent=2) + '\n')
(out / 'loader-config-before-private.conf').write_bytes(original_config)
config_meta = config.stat()
installed = Path('/lib/apk/db/installed').read_bytes()
configuration = b'options qcom_pm8008 experimental_p_imx319_power=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008\n'
def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
def atomic(path, data, mode=0o644, uid=0, gid=0):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.k235-', dir=path.parent)
    temp = Path(name)
    try:
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(data)
                stream.flush()
            os.fchmod(fd, mode)
            os.fchown(fd, uid, gid)
            os.fsync(fd)
        finally:
            os.close(fd)
        assert temp.read_bytes() == data
        os.replace(temp, path)
        sync_directory(path.parent)
    finally:
        if temp.exists():
            temp.unlink()
def state(phase):
    atomic(out / 'transaction-state-private.json', (json.dumps(dict(stage=235, state=phase,
           runtime_reloaded=False, transition_sent=False)) + '\n').encode(), 0o600)
def live_unchanged():
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
    assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
    assert all(Path('/sys/module', name, 'notes/.note.gnu.build-id').read_bytes() == value for name, value in loaded.items())
    assert Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').read_text().strip() == 'Y'
    assert not Path('/sys/module/imx319').exists() and not Path('/sys/module/qcom_pm8008_imx319_lab').exists()
    assert all(Path('/sys/bus/i2c/devices', name, 'driver').resolve().name == 'pm8008' for name in ['1-0004', '1-0008'])
    assert Path('/lib/apk/db/installed').read_bytes() == installed
state('prepared')
try:
    atomic(config, configuration, stat.S_IMODE(config_meta.st_mode), config_meta.st_uid, config_meta.st_gid)
    for name, (_, candidate) in mapping.items():
        metadata = saved.get(name, dict(mode=0o644, uid=0, gid=0))
        atomic(tree / name, candidate.read_bytes(), **metadata)
    state('module_files_installed')
    result = subprocess.run(['depmod', '-a', os.uname().release], capture_output=True, timeout=45)
    (out / 'depmod-private.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0
    plan = subprocess.run(['modprobe', '--show-depends', 'qcom_pm8008'], capture_output=True, timeout=15)
    (out / 'kmod-pmic-plan-private.log').write_bytes(plan.stdout + plan.stderr)
    assert plan.returncode == 0
    lines = [line for line in plan.stdout.decode().splitlines() if line.startswith('insmod ')]
    assert len(lines) == 2 and 'reset-realme-rmx1931-pm8008.ko' in lines[0]
    assert 'qcom-pm8008.ko' in lines[1] and 'experimental_p_imx319_power=1' in lines[1]
    for alias, expected in [('platform:pm8008-reg-lab14', 'qcom_pm8008_imx319_lab'),
                            ('of:NcameraT(null)Crealme,rmx1931-imx319', 'imx319')]:
        result = subprocess.run(['modprobe', '-R', alias], capture_output=True, timeout=15)
        (out / (expected + '-alias-private.log')).write_bytes(result.stdout + result.stderr)
        assert result.returncode == 0 and result.stdout.decode().strip().replace('-', '_') == expected
    actual = inventory_now()
    ko = {name: digest for name, digest in actual.items() if name.endswith('.ko')}
    expected = {name: digest for name, digest in inventory.items() if name.endswith('.ko')}
    expected.update({name: lock['files'][key]['sha256'] for name, (key, _) in mapping.items()})
    assert ko == expected and len(ko) == 775 and len(actual) == 789
    assert config.read_bytes() == configuration
    live_unchanged()
    (out / 'module-inventory-after-private.json').write_text(json.dumps(actual, indent=2) + '\n')
    (out / 'module-tree-after.sha256').write_text(''.join(digest + '  ' + name + '\n' for name, digest in sorted(actual.items())))
    (out / 'loader-config-after.sha256').write_text(sha(configuration) + '  ' + str(config) + '\n')
    state('verified')
except BaseException:
    live_unchanged()
    errors = []
    def restore(operation):
        try:
            operation()
        except BaseException as error:
            errors.append(type(error).__name__)
    for name, metadata in saved.items():
        restore(lambda name=name, metadata=metadata: atomic(tree / name, (backup / name).read_bytes(), **metadata))
    for name in actual if 'actual' in locals() else inventory_now():
        if name not in inventory:
            path = tree / name
            # Only our two exact module paths or new depmod metadata may be removed.
            assert name in mapping or not name.endswith('.ko')
            restore(lambda path=path: path.unlink())
    restore(lambda: atomic(config, original_config, stat.S_IMODE(config_meta.st_mode), config_meta.st_uid, config_meta.st_gid))
    assert not errors and inventory_now() == inventory and config.read_bytes() == original_config
    live_unchanged()
    try:
        state('rolled_back_files')
    except BaseException:
        pass
    raise
report = dict(stage=235, three_module_files_staged=True, module_ko_count=775, module_related_files=789,
              default_off_lab_opt_in_staged=True, kmod_order_and_two_aliases_verified=True,
              current232_pmic_and_front_runtime_unchanged=True, provider_file_unchanged=True,
              package_database_unchanged=True, taint=0, no_reload_power_capture_reboot_or_flash=True)
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
