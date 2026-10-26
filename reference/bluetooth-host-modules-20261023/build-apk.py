"""Prepare/sign only the real successful BNEP/UHID k363 artifacts supplied later.

This script never compiles modules, generates signing keys, accesses the SDK or
device, installs an APK, invokes modprobe/insmod/depmod, or edits an existing
artifact. All three payload paths are fixed. Current source preparation alone
is not permission or evidence that module building/signing has happened.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import stat
import struct
import subprocess

HERE = Path(__file__).resolve().parent
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
VERMAGIC = RELEASE + ' SMP preempt mod_unload aarch64'
CONFIG_SHA256 = '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
SYMVERS_SHA256 = '0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223'
COMMIT = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
TARGETS = {
    'bnep': 'usr/lib/modules/' + RELEASE + '/kernel/net/bluetooth/bnep/bnep.ko',
    'uhid': 'usr/lib/modules/' + RELEASE + '/kernel/drivers/hid/uhid.ko',
}
CONF = '60-samurai-bluetooth-host.conf'
PACKAGE_NAME = 'samurai-bluetooth-host-k363'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module_view(raw, name):
    require(raw[:6] == b'\x7fELF\x02\x01', 'Expected little-endian ELF64')
    require(struct.unpack_from('<HH', raw, 16) == (1, 183), 'Expected AArch64 relocatable module')
    offset = struct.unpack_from('<Q', raw, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', raw, 58)
    require(size == 64 and names_index < count and offset + size * count <= len(raw), 'Invalid section table')
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + n * size) for n in range(count)]
    section_names = raw[rows[names_index][4]:rows[names_index][4] + rows[names_index][5]]
    sections = {}
    for row in rows:
        label = section_names[row[0]:].split(b'\0', 1)[0].decode('ascii')
        if row[1] != 8:
            require(row[4] + row[5] <= len(raw), 'Section outside artifact')
            sections[label] = raw[row[4]:row[4] + row[5]]
    fields = {}
    for item in sections['.modinfo'].split(b'\0'):
        if b'=' in item:
            key, value = item.split(b'=', 1)
            fields.setdefault(key.decode(), []).append(value.decode())
    require(fields.get('name') == [name] and fields.get('intree') == ['Y'], 'Wrong name or missing intree=Y')
    require(fields.get('vermagic') == [VERMAGIC], 'Module is not the original363 ABI')
    symtab = next(row for row in rows if row[1] == 2)
    require(symtab[9] == 24 and symtab[5] % 24 == 0 and symtab[6] < count, 'Invalid symbol table')
    strings = raw[rows[symtab[6]][4]:rows[symtab[6]][4] + rows[symtab[6]][5]]
    imports = set()
    for at in range(symtab[4], symtab[4] + symtab[5], 24):
        name_offset, info, other, index, value, length = struct.unpack_from('<IBBHQQ', raw, at)
        if index == 0 and info >> 4 in (1, 2) and name_offset:
            imports.add(strings[name_offset:].split(b'\0', 1)[0].decode())
    require(imports and '.note.gnu.build-id' in sections, 'Missing imported symbols or build-id')
    ordered_imports = sorted(imports)
    return dict(name=name, sha256=sha(raw), bytes=len(raw), vermagic=VERMAGIC, intree='Y',
                build_id_note_sha256=sha(sections['.note.gnu.build-id']),
                imports_sha256=sha(('\n'.join(ordered_imports) + '\n').encode()),
                imported_symbols=ordered_imports, depends=fields.get('depends', [''])[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['validation', 'kernel-validation', 'inputs-lock', 'symvers', 'bnep', 'uhid', 'apk', 'sign-key', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(os.name == 'posix' and os.geteuid() == 0, 'Use an isolated Linux filesystem build root')
    require(args.build_root.is_absolute() and not args.build_root.exists() and not str(args.build_root).startswith('/mnt/'), 'New Linux build directory required')
    require(args.output.is_absolute() and not args.output.exists(), 'New output directory required')
    validation_bytes = args.validation.read_bytes()
    validation = json.loads(validation_bytes)
    lock = json.loads(args.inputs_lock.read_bytes())
    require(validation.get('passed') is True, 'No actual successful host-module build; signing refused')
    require(lock.get('build_validation_sha256') == sha(validation_bytes), 'Original successful report is not locked')
    kernel_bytes = args.kernel_validation.read_bytes()
    kernel = json.loads(kernel_bytes)
    require(lock.get('kernel_validation_sha256') == sha(kernel_bytes), 'Original363 report is not locked')
    require(kernel['commit'] == COMMIT and kernel['release'] == RELEASE, 'Wrong original363 source/release')
    require(kernel['artifacts']['.config']['sha256'] == CONFIG_SHA256, 'Original363 config proof missing')
    require(kernel['artifacts']['Module.symvers']['sha256'] == SYMVERS_SHA256, 'Original363 symbol-table proof missing')
    require(validation.get('terminal') is True and validation.get('exit') == 0 and validation.get('restore_private_config_exit') == 0 and not validation.get('diagnostics'), 'Build or restoration was not clean')
    for field in ['original363_config_and_symvers_verified', 'only_two_semantic_config_changes',
                  'private_qca_config_restored', 'shared_inputs_and_pm_modules_unchanged']:
        require(validation.get(field) is True, 'Build proof missing: ' + field)
    require(validation.get('image_built') is False and validation.get('installed_or_loaded') is False, 'Unexpected build/deployment scope')
    require(validation.get('configuration_delta') == {'CONFIG_BT_BNEP': ['n', 'm'], 'CONFIG_UHID': ['n', 'm']}, 'Unexpected configuration delta')
    reported = {row['name']: row for row in validation['modules']}
    require(len(validation['modules']) == 2 and set(reported) == set(TARGETS) and set(lock['modules']) == set(TARGETS), 'Only the two original module locks are allowed')
    symvers = args.symvers.read_bytes()
    require(sha(symvers) == SYMVERS_SHA256, 'Actual input is not the original363 Module.symvers')
    available = {line.split()[1] for line in symvers.decode().splitlines() if line.split()}
    sources, views = {}, {}
    require(args.bnep.resolve() != args.uhid.resolve(), 'The two original inputs must be distinct')
    for name in TARGETS:
        path = getattr(args, name)
        require(path.is_file() and not path.is_symlink(), 'Use the original regular module file')
        raw = path.read_bytes()
        view = module_view(raw, name)
        for key in ['sha256', 'bytes', 'build_id_note_sha256', 'imports_sha256']:
            require(lock['modules'][name].get(key) == view[key], 'Original module lock differs: ' + name + '/' + key)
        row = reported[name]
        require(row.get('sha256') == view['sha256'] and row.get('bytes') == view['bytes'], 'Module differs from actual successful build report')
        require(row.get('vermagic') == VERMAGIC and row.get('intree') == 'Y' and row.get('depends') == view['depends'] == '', 'Reported ABI differs')
        require(row.get('imports_in_original363') is True and row.get('imported_symbols') == len(view['imported_symbols']), 'Reported imports differ')
        require(set(view['imported_symbols']) <= available, 'Unresolved import against original363 symbols: ' + name)
        sources[name], views[name] = raw, view
    conf = (HERE / CONF).read_bytes()
    require(conf == b'bnep\nuhid\n', 'The configuration must contain exactly the two module names')
    require(args.sign_key.is_file() and args.verification_keys.is_dir(), 'Existing trusted signing inputs required')
    # All input/report checks happen before output creation; do not invent locks
    # by hashing newly produced package files or accepting a mere passed flag.
    args.build_root.mkdir(parents=True, mode=0o700)
    args.output.mkdir(parents=True, mode=0o700)
    payload = args.build_root / 'payload'
    srcdir = args.build_root / 'source'
    payload.mkdir()
    srcdir.mkdir()
    for name, raw in sources.items():
        (srcdir / (name + '.ko')).write_bytes(raw)
    (srcdir / CONF).write_bytes(conf)
    recipe = (HERE / 'APKBUILD.in').read_text()
    for key, raw in [('BNEP', sources['bnep']), ('UHID', sources['uhid']), ('CONF', conf)]:
        recipe = recipe.replace('@' + key + '_SHA512@', hashlib.sha512(raw).hexdigest())
    recipe_path = srcdir / 'APKBUILD'
    recipe_path.write_text(recipe)
    stage = subprocess.run(['/bin/sh', '-c', 'set -eu; . "$1"; package', 'stage-host-modules', str(recipe_path)],
                           env=dict(os.environ, srcdir=str(srcdir), pkgdir=str(payload)), capture_output=True)
    (args.build_root / 'package-function.log').write_bytes(stage.stdout + stage.stderr)
    require(stage.returncode == 0, 'Three-file package() staging failed')
    expected = {TARGETS[name]: raw for name, raw in sources.items()}
    expected['usr/lib/modules-load.d/' + CONF] = conf
    files = {}
    require({str(path.relative_to(payload)) for path in payload.rglob('*') if path.is_file()} == set(expected), 'Unexpected payload')
    epoch = 1792713600
    for path in [*payload.rglob('*'), payload]:
        os.chown(path, 0, 0)
        os.utime(path, (epoch, epoch))
    for target, raw in expected.items():
        path = payload / target
        require(path.read_bytes() == raw and stat.S_IMODE(path.stat().st_mode) == 0o644, 'Staged payload/mode differs')
        files[target] = dict(sha256=sha(raw), bytes=len(raw), mode=0o644)
    metadata = dict(name=PACKAGE_NAME, version='0.1.0-r0', arch='aarch64', license='GPL-2.0-only',
        origin=PACKAGE_NAME, description='Realme X2 Pro k363 BNEP and UHID host modules',
        maintainer='Realme X2 Pro Linux port', url='https://github.com/hmhmdcy/pmaports',
        depends='bluez kmod openrc', **{'build-time': str(epoch)})
    apk_path = args.output / (PACKAGE_NAME + '-0.1.0-r0.apk')
    command = [str(args.apk), 'mkpkg', '--compat', '3.0.0', '--compression', 'deflate:9', '--files', str(payload),
               '--sign-key', str(args.sign_key), '--output', str(apk_path)]
    for key, value in sorted(metadata.items()):
        command += ['--info', key + ':' + value]
    for label, invocation in [('mkpkg', command), ('verify', [str(args.apk), '--keys-dir', str(args.verification_keys), 'verify', str(apk_path)])]:
        result = subprocess.run(invocation, capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, label + ' failed')
    for name, raw in sources.items():
        require(getattr(args, name).read_bytes() == raw, 'Original module changed during packaging')
    package_digest = sha(apk_path.read_bytes())
    manifest = dict(schema=1, package=apk_path.name, sha256=package_digest, bytes=apk_path.stat().st_size,
        metadata=metadata, files=files, modules=views, build_validation_sha256=sha(validation_bytes),
        kernel_validation_sha256=sha(kernel_bytes), original363_symvers_sha256=sha(symvers),
        inputs_lock_sha256=sha(args.inputs_lock.read_bytes()), signature_verified=True,
        install_hooks_present=False, service_files_present=False, device_installed=False,
        independent_readback_and_isolated_install_validation_pending=True,
        current_device_modules_order_owner_identity_and_manifest_preflight_pending=True)
    manifest_path = args.output / 'package-manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    # Independent path names and a post-manifest readback prevent repeating the
    # old path-variable bug that once wrote JSON over a different package.
    require(sha(apk_path.read_bytes()) == package_digest, 'APK changed after manifest write')
    print(json.dumps(dict(package=apk_path.name, sha256=package_digest, file_count=3, device_installed=False)))


if __name__ == '__main__':
    main()
