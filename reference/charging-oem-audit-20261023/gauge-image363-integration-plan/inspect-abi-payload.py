"""Read current formal camera artifacts and original 363 initramfs manifest."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
PRIVATE = Path('/mnt/e/edk2-samurai-out')
spec = importlib.util.spec_from_file_location('gauge_plan_abi_storage284', REF / 'kernel284/storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
mount = Path('/mnt/samurai-full282')
mounted = [line for line in Path('/proc/self/mountinfo').read_text().splitlines()
           if line.split()[4] == str(mount)]
if mounted:
    assert len(mounted) == 1 and ' - ext4 /dev/loop' in mounted[0]
    device = mounted[0].split(' - ext4 ', 1)[1].split()[0]
    backing = Path('/sys/class/block', Path(device).name, 'loop/backing_file').read_text().strip()
    assert Path(backing).resolve() == (PRIVATE / 'kernel282/full-kernel-build282.ext4').resolve()
    assert (PRIVATE / 'kernel282/full-kernel-build282.ext4').stat().st_size == 32 * 1024**3
    build = mount / 'build'  # Existing exact mount: no lock ownership change.
else:
    build = storage.mounted_build()


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def output(argv):
    return subprocess.check_output(argv, text=True)


symvers = build / 'Module.symvers'
assert digest(symvers) == '0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223'
symbols = {line.split()[1]: line.split() for line in symvers.read_text().splitlines()}
wrapper = PRIVATE / 'kernel481/formal-expected-private.json'
assert digest(wrapper) == '1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
expected = json.loads(wrapper.read_bytes())['expected']
artifacts = {}
for name, entry in expected['modules'].items():
    basename = Path(entry['path']).stem
    files = list((PRIVATE / 'kernel441').glob(basename + '-intree-r4.ko'))
    assert len(files) == 1 and digest(files[0]) == entry['sha256'], name
    artifacts[name] = files[0]
sensor_hash = next(v for k, v in expected['installed_files'].items() if k.endswith('/s5k3m5.ko'))
sensor = PRIVATE / 'kernel468/s5k3m5-mode2-build2.ko'
assert digest(sensor) == sensor_hash == '494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392'
artifacts['s5k3m5'] = sensor
imports, exports, module_info = {}, {}, {}
for name, path in artifacts.items():
    imports[name] = sorted({line.split()[-1] for line in output(['aarch64-linux-gnu-nm', '-u', str(path)]).splitlines() if line.strip()})
    exports[name] = sorted({line.split()[-1].removeprefix('__ksymtab_') for line in
        output(['aarch64-linux-gnu-nm', '-a', '--defined-only', str(path)]).splitlines()
        if line.split()[-1].startswith('__ksymtab_') and line.split()[-1] != '__ksymtab_strings'})
    module_info[name] = {'sha256': digest(path), 'bytes': path.stat().st_size,
        'vermagic': output(['modinfo', '-F', 'vermagic', str(path)]).strip(),
        'depends': output(['modinfo', '-F', 'depends', str(path)]).strip()}
available_group = set().union(*(set(v) for v in exports.values()))
dependency_exports = {}
dependency_receipt = json.loads((REF / 'kernel441/intree-build-validation.json').read_bytes())
for entry in dependency_receipt['modules']:
    if entry['runtime_candidate']:
        continue
    path = Path(entry['private_path'])
    assert digest(path) == entry['sha256']
    names = {line.split()[-1].removeprefix('__ksymtab_') for line in
        output(['aarch64-linux-gnu-nm', '-a', '--defined-only', str(path)]).splitlines()
        if line.split()[-1].startswith('__ksymtab_') and line.split()[-1] != '__ksymtab_strings'}
    dependency_exports[entry['name']] = {'sha256': digest(path), 'exports': sorted(names)}
available_dependencies = set().union(*(set(v['exports']) for v in dependency_exports.values()))
for name in artifacts:
    needed = set(imports[name])
    module_info[name].update(import_count=len(needed),
        imports_from_original363=len(needed & symbols.keys()),
        imports_from_current_camera_group=sorted((needed - symbols.keys()) & available_group),
        imports_from_cached_dependency_artifacts=sorted((needed - symbols.keys() - available_group) & available_dependencies),
        unresolved_imports=sorted(needed - symbols.keys() - available_group - available_dependencies))
    assert not module_info[name]['unresolved_imports'], name
manifest_path = PRIVATE / 'kernel363/boot-initramfs-manifest-private.json'
manifest = json.loads(manifest_path.read_bytes())
root = build.parent / 'input-initramfs363'
actual = {}
for p in root.rglob('*'):
    info = p.lstat()
    row = dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid)
    if p.is_symlink():
        row.update(kind='symlink', target=os.readlink(p))
    elif p.is_file():
        row.update(kind='file', sha256=digest(p))
    elif p.is_dir():
        row.update(kind='directory')
    else:
        row.update(kind='special', rdev=info.st_rdev)
    actual[str(p.relative_to(root))] = row
assert len(actual) == 396 and actual == manifest
config_path = PRIVATE / 'kernel457/config363-private'
assert digest(config_path) == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
config = config_path.read_text()
selected = {key: next((line for line in config.splitlines() if line.startswith(key + '=') or
                        line == '# ' + key + ' is not set'), 'absent / disabled')
            for key in ['CONFIG_MODVERSIONS', 'CONFIG_LTO_NONE', 'CONFIG_MODULE_SIG',
            'CONFIG_TRIM_UNUSED_KSYMS', 'CONFIG_RANDSTRUCT_NONE', 'CONFIG_BATTERY_BQ27XXX',
            'CONFIG_BATTERY_BQ27XXX_I2C', 'CONFIG_LOCALVERSION', 'CONFIG_LOCALVERSION_AUTO',
            'CONFIG_INITRAMFS_SOURCE', 'CONFIG_VIDEO_QCOM_CAMSS', 'CONFIG_DEBUG_INFO_BTF',
            'CONFIG_RUST', 'CONFIG_GENERIC_BUILTIN_DTB']}
result = {'formal_camera_wrapper_sha256': digest(wrapper), 'modules': module_info,
    'module_imports': imports, 'module_exports': exports,
    'cached_dependency_artifacts': dependency_exports,
    'dependency_artifacts_are_cached_builds_not_runtime_attestation': True,
    'original363_Module_symvers_sha256': digest(symvers), 'exact_Image363_config_sha256': digest(config_path),
    'config_363_private_path': str(config_path), 'selected_config': selected,
    'initramfs_manifest_sha256': digest(manifest_path), 'initramfs_entries': len(actual),
    'original363_initramfs_payload_exact': True,
    'embedded_BT_modules': {k: v['sha256'] for k, v in manifest.items() if k.endswith('.ko')},
    'note': 'imports/provider names only; MODVERSIONS is off, zero CRC is not extra ABI proof',
    'compile_link_object_test_executed': False, 'sdk_device_accessed': False, 'shared_files_written': False}
(HERE / 'abi-payload.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'modules': module_info, 'payload_exact': True, 'selected_config': selected}), flush=True)
