"""Plan two small module targets; execute only after the explicit 456 handoff.

Reuses the existing private QCA source-view/O. No new O, Image, SDK or device.
The default path is read-only and never invokes make or changes configuration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/bluetooth-host-config-20261023')
ROOT = Path('/mnt/samurai-full282')
ORIGINAL = ROOT / 'source354'
SHARED = ROOT / 'build'
ISOLATED = ROOT / 'bluetooth-transport-20261023'
SOURCE = ISOLATED / 'source-view'
BUILD = ISOLATED / 'O'
COMMIT = 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
TARGETS = ['net/bluetooth/bnep/bnep.ko', 'drivers/hid/uhid.ko']
CHANGES = {'CONFIG_BT_BNEP': ('n', 'm'), 'CONFIG_UHID': ('n', 'm')}
FILTERS = {'CONFIG_BT_BNEP_MC_FILTER': 'n', 'CONFIG_BT_BNEP_PROTO_FILTER': 'n'}
SOURCE_FILES = ['net/bluetooth/Kconfig', 'net/bluetooth/Makefile',
    'net/bluetooth/bnep/Kconfig', 'net/bluetooth/bnep/Makefile',
    'net/bluetooth/bnep/bnep.h', 'net/bluetooth/bnep/core.c',
    'net/bluetooth/bnep/sock.c', 'net/bluetooth/bnep/netdev.c',
    'drivers/hid/uhid.c', 'drivers/hid/Makefile', 'drivers/hid/Kconfig',
    'include/linux/hid.h', 'include/uapi/linux/uhid.h', 'include/uapi/linux/hid.h',
    'include/net/bluetooth/bluetooth.h', 'include/net/bluetooth/hci_core.h']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(path):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + str(ORIGINAL),
        '-C', str(ORIGINAL), 'show', COMMIT + ':' + path])


def config(raw):
    result = {}
    for line in raw.decode().splitlines():
        if line.startswith('CONFIG_'):
            key, value = line.split('=', 1)
            result[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            result[line[2:-11]] = 'n'
    return result


def differences(before, after):
    return {key: [before.get(key, 'n'), after.get(key, 'n')]
            for key in before.keys() | after.keys()
            if before.get(key, 'n') != after.get(key, 'n')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-after-456-handoff', action='store_true',
                        help='Use only after the main session confirms camera456 resource handoff')
    args = parser.parse_args()
    plan = dict(execute=args.execute_after_456_handoff, source_view=str(SOURCE), output=str(BUILD),
                no_new_big_output_tree=True, parallel_jobs=1, targets=TARGETS,
                configuration_delta=CHANGES, image_or_sdk_or_device=False,
                resource_handoff_required=True)
    if not args.execute_after_456_handoff:
        print(json.dumps(plan, indent=2))
        return 0

    # No automatic mount or resource takeover. A missing mount is a stop.
    assert ORIGINAL.is_dir() and (BUILD / '.config').is_file(), 'Existing mounted private QCA O required'
    assert (BUILD / 'include/config/kernel.release').read_text().strip() == RELEASE
    assert shutil.disk_usage(ROOT).free >= (2 * 1024**3 + 128 * 1024**2), 'Keep 2 GiB plus a small target budget free'
    record = json.loads((R.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
    assert record['commit'] == COMMIT and record['release'] == RELEASE
    assert sha(SHARED / 'Module.symvers') == record['artifacts']['Module.symvers']['sha256']
    for path in SOURCE_FILES:
        assert (SOURCE / path).resolve() == (ORIGINAL / path).resolve(), 'Source view must read unchanged module sources'
        assert (ORIGINAL / path).read_bytes() == git(path), 'Relevant source/header differs from fixed k363: ' + path

    original_config = (BUILD / '.config').read_bytes()
    before_config = config(original_config)
    image = P.parent / 'kernel363/Image-k363-private'
    assert sha(image) == record['artifacts']['arch/arm64/boot/Image']['sha256']
    image_config = subprocess.check_output([str(ORIGINAL / 'scripts/extract-ikconfig'), str(image)])
    assert hashlib.sha256(image_config).hexdigest() == record['artifacts']['.config']['sha256']
    assert not differences(config(image_config), before_config), 'Private O has a semantic configuration change beyond k363'
    assert all(before_config.get(k) == old for k, (old, new) in CHANGES.items())
    assert all(before_config.get(k) == 'y' for k in ['CONFIG_BT', 'CONFIG_BT_BREDR',
        'CONFIG_HID_SUPPORT', 'CONFIG_HID', 'CONFIG_HID_GENERIC', 'CONFIG_CRC32'])
    assert before_config.get('CONFIG_BT_LE') == 'n'
    assert before_config.get('CONFIG_MODVERSIONS') == 'n'
    assert (BUILD / 'Module.symvers').is_file()
    private_symvers = (BUILD / 'Module.symvers').read_bytes()
    P.mkdir(exist_ok=True)
    assert not (P / 'build-state.json').exists(), 'Inspect the prior transaction; do not replay it'
    (P / 'config-before-private').write_bytes(original_config)
    (P / 'module-symvers-before-private').write_bytes(private_symvers)

    guarded = [SHARED / key for key in ['.config', 'Module.symvers', 'include/config/kernel.release',
        'include/config/auto.conf', 'include/generated/autoconf.h', 'include/generated/utsrelease.h']]
    guarded += [ORIGINAL / key for key in SOURCE_FILES]
    pm_report = json.loads((R.parent / 'bluetooth-transport-20261023/qca-pm-r2-module-build-validation.json').read_text())
    guarded += [Path(pm_report['private_module']), Path(pm_report['stripped_module'])]
    hashes = {str(path): sha(path) for path in guarded}
    fragment = config((R / 'modules.config').read_bytes())
    assert fragment == dict({key: new for key, (old, new) in CHANGES.items()}, **FILTERS), 'Unexpected fragment options'
    assert all(before_config.get(key, 'n') == 'n' for key in FILTERS)
    lines = original_config.decode().splitlines()
    for key, value in fragment.items():
        lines = [line for line in lines if not line.startswith(key + '=')
                 and line != '# ' + key + ' is not set']
        lines.append('# ' + key + ' is not set' if value == 'n' else key + '=' + value)
    text = '\n'.join(lines) + '\n'
    assert differences(before_config, config(text.encode())) == {
        key: [old, new] for key, (old, new) in CHANGES.items()}

    env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
        RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder',
        KBUILD_BUILD_HOST='samurai', KBUILD_BUILD_VERSION='363', TMPDIR=str(ISOLATED / 'tmp'))
    for key in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG']:
        env.pop(key, None)
    common = ['make', '-C', str(SOURCE), 'O=' + str(BUILD), 'ARCH=arm64',
        'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'KERNELRELEASE=' + RELEASE,
        'W=1', 'KCFLAGS=-Werror', '-j1']
    log = P / 'build-private.log'
    phases, modules = [], []
    ret, restore, failure = None, None, None
    began = time.monotonic()
    try:
        (BUILD / '.config').write_text(text)
        shutil.copyfile(SHARED / 'Module.symvers', BUILD / 'Module.symvers')
        with log.open('xb') as handle:
            for targets in [['olddefconfig'], ['modules_prepare'], TARGETS]:
                start = time.monotonic()
                proc = subprocess.Popen(common + targets, env=env, stdout=handle, stderr=subprocess.STDOUT)
                (P / 'build-state.json').write_text(json.dumps(dict(terminal=False, target=targets, pid=proc.pid)) + '\n')
                ret = proc.wait()
                phases.append(dict(target=targets, exit=ret, seconds=round(time.monotonic() - start, 3)))
                if ret:
                    break
                assert differences(before_config, config((BUILD / '.config').read_bytes())) == {
                    key: [old, new] for key, (old, new) in CHANGES.items()}
            if not ret:
                available = {line.split()[1] for line in (SHARED / 'Module.symvers').read_text().splitlines()}
                for name, target in zip(['bnep', 'uhid'], TARGETS):
                    output = P / (name + '-k363-intree.ko')
                    shutil.copyfile(BUILD / target, output)
                    subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(output)], check=True)
                    info = lambda field: subprocess.check_output(['modinfo', '-F', field, str(output)], text=True).strip()
                    imported = {line.split()[-1] for line in subprocess.check_output(
                        ['aarch64-linux-gnu-nm', '-u', str(output)], text=True).splitlines() if line.strip()}
                    assert imported <= available, imported - available
                    assert info('intree') == 'Y' and info('vermagic') == pm_report['vermagic']
                    modules.append(dict(name=name, path=str(output), bytes=output.stat().st_size,
                        sha256=sha(output), intree=info('intree'), vermagic=info('vermagic'),
                        depends=info('depends'), imported_symbols=len(imported), imports_in_original363=True))
    except Exception as exc:
        failure = repr(exc)
        ret = ret if ret else 1
    finally:
        # Restore only our private O metadata for later QCA reuse, never shared inputs.
        (BUILD / '.config').write_bytes(original_config)
        with (P / 'restore-private-config.log').open('xb') as handle:
            restore = subprocess.run(common + ['olddefconfig'], env=env,
                                     stdout=handle, stderr=subprocess.STDOUT).returncode
        (BUILD / 'Module.symvers').write_bytes(private_symvers)
        assert not differences(before_config, config((BUILD / '.config').read_bytes()))
        assert {str(path): sha(path) for path in guarded} == hashes, 'A guarded input changed; do not proceed'
    diagnostics = [line for line in log.read_text(errors='replace').splitlines()
                   if 'warning:' in line.lower() or 'error:' in line.lower()]
    result = dict(plan, terminal=True, exit=ret, restore_private_config_exit=restore, phases=phases,
        seconds=round(time.monotonic() - began, 3), diagnostics=diagnostics, modules=modules, failure=failure,
        passed=ret == 0 and restore == 0 and not diagnostics and len(modules) == 2,
        original363_config_and_symvers_verified=True, only_two_semantic_config_changes=True,
        private_qca_config_restored=True, shared_inputs_and_pm_modules_unchanged=True,
        image_built=False, installed_or_loaded=False)
    (P / 'build-state.json').write_text(json.dumps(result, indent=2) + '\n')
    (R / 'module-build-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
