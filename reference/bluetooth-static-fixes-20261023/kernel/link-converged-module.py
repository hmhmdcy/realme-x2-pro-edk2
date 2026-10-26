"""Link the validated two-object candidate in the existing owned k363 O.

No mount, source354/shared build/SDK write, Image, package or device action.
Use only after the explicitly coordinated kernel resource window. Every
temporary source/object/module/index write is backed up and restored.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time

R = Path(__file__).resolve().parent
REF = R.parents[1]
OLD = Path('/mnt/e/edk2-samurai-out/bluetooth-static-fixes-20261023/kernel')
P = OLD / 'converged'
ROOT = Path('/mnt/samurai-full282')
SRC = ROOT / 'source354'
VIEW = ROOT / 'bluetooth-transport-20261023/source-view'
O = ROOT / 'bluetooth-transport-20261023/O'
SHARED = ROOT / 'build'
REL = '7.3.0-rc6-rmx1931-samurai-k363+'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def config(raw):
    result = {}
    for line in raw.decode().splitlines():
        if line.startswith('CONFIG_'):
            key, value = line.split('=', 1)
            result[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            result[line[2:-11]] = 'n'
    return result


def output(command):
    return subprocess.check_output(command, text=True).strip()


assert (O / '.config').exists(), 'Owned mounted O absent; do not create another O'
assert shutil.disk_usage(ROOT).free >= 2 * 1024**3 + 128 * 1024**2
lock = json.loads((R / 'source-lock.json').read_text())
objects = json.loads((R / 'object-build-validation.json').read_text())
assert objects['passed'] and objects['guarded_inputs_unchanged']
assert objects['candidate_sha256'] == lock['candidate_sha256']
assert (O / 'include/config/kernel.release').read_text().strip() == REL
assert sha(SHARED / 'Module.symvers') == '0837fdc36f1bd6ab16109d4852883566b8fe42e5bb640771e30afb7822779223'
assert sha(O / '.config') == '64c8d7893685dc5634de84a814f69d5a5ec7f274990c0ddff70801a8193d231e'
assert sha(O / 'Module.symvers') == '881c968b99f7ae411878b991156dfe046a9294c8209700d2fc5492ac5c2e813d'
original_record = json.loads((REF / 'kernel363/boot-candidate-build-validation.json').read_text())
image = OLD.parents[1] / 'kernel363/Image-k363-private'
assert sha(image) == original_record['artifacts']['arch/arm64/boot/Image']['sha256']
image_config = subprocess.check_output([str(SRC / 'scripts/extract-ikconfig'), str(image)])
assert hashlib.sha256(image_config).hexdigest() == original_record['artifacts']['.config']['sha256']
a, b = config(image_config), config((O / '.config').read_bytes())
assert not {k: (a.get(k, 'n'), b.get(k, 'n')) for k in a.keys() | b.keys() if a.get(k, 'n') != b.get(k, 'n')}
assert b['CONFIG_MODVERSIONS'] == 'n' and b['CONFIG_MODULE_SIG'] == 'n'
for name, entry in lock['baseline'].items():
    assert sha(SRC / 'drivers/bluetooth' / name) == entry['sha256']
    assert sha(R / 'candidate' / name) == lock['candidate_sha256'][name]
for obj in objects['objects']:
    assert sha(Path(obj['path'])) == obj['sha256']
assert (O / 'vmlinux.o').is_symlink() and (O / 'vmlinux.o').resolve() == SHARED / 'vmlinux.o'

members = (O / 'drivers/bluetooth/hci_uart.mod').read_text().splitlines()
assert members == ['drivers/bluetooth/' + stem + '.o' for stem in
    ['hci_ldisc', 'hci_serdev', 'hci_h4', 'hci_ll', 'hci_bcm', 'hci_qca', 'hci_mrvl']]
members += ['drivers/bluetooth/btbcm.o', 'drivers/bluetooth/btqca.o']
assert all((O / name).is_file() for name in members)
P.mkdir(exist_ok=False)
(P / 'backup').mkdir()
shutil.copyfile(SHARED / 'Module.symvers', P / 'original363-Module.symvers')
protected = [SHARED / n for n in ['.config', 'Module.symvers', 'include/config/kernel.release']]
protected += [O / n for n in ['.config', 'include/config/auto.conf', 'include/generated/autoconf.h',
    'include/generated/utsrelease.h', 'include/config/kernel.release', 'scripts/module.lds']]
protected += [SRC / 'drivers/bluetooth' / n for n in ['hci_serdev.c', 'hci_qca.c', 'hci_ldisc.c', 'hci_uart.h', 'Makefile', 'Kconfig']]
protected += [Path(entry['path']) for entry in objects['objects']]
pm = OLD.parents[1] / 'bluetooth-transport-20261023'
protected += [pm / n for n in ['hci_uart-qca-pm-r2-k363-intree.ko',
    'hci_uart-qca-pm-r2-k363-intree-stripped.ko', 'qcom_geni_serial-rts-candidate.o', 'hci_qca-pm-r2.c']]
protected += [R / 'source-lock.json', R / 'object-build-validation.json', R / 'offline-validation.json']
protected += [R / name for name in lock['artifact_files']]
guard = {str(p): sha(p) for p in protected}

# Exact small write set: 9 members + their commands, 3 modules + generated
# metadata, two owned source files, and Kbuild's module indexes/common object.
mutable = set()
for relative in members:
    p = O / relative
    mutable.update([p, p.with_name('.' + p.name + '.cmd')])
for module in ['hci_uart', 'btbcm', 'btqca']:
    for suffix in ['.o', '.ko', '.mod', '.mod.c', '.mod.o']:
        p = O / 'drivers/bluetooth' / (module + suffix)
        mutable.update([p, p.with_name('.' + p.name + '.cmd')])
for relative in ['Module.symvers', 'modules.order', 'modules-only.symvers', 'vmlinux.symvers',
                 '.module-common.o', 'drivers/bluetooth/modules.order']:
    p = O / relative
    mutable.update([p, p.with_name('.' + p.name + '.cmd')])
mutable.update(VIEW / 'drivers/bluetooth' / n for n in lock['candidate_sha256'])
snapshot = {}
for index, path in enumerate(sorted(mutable)):
    record = dict(existed=path.exists() or path.is_symlink(), symlink=None, sha256=None, backup=None)
    if path.is_symlink():
        record.update(symlink=os.readlink(path), sha256=sha(path))
    elif path.exists():
        target = P / 'backup' / str(index)
        shutil.copy2(path, target)
        record.update(backup=str(target.relative_to(P)), sha256=sha(path))
    snapshot[str(path)] = record
(P / 'before-private.json').write_text(json.dumps(dict(guard=guard, mutable=snapshot), indent=2) + '\n')
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
    RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai',
    KBUILD_BUILD_VERSION='363', TMPDIR=str(ROOT / 'bluetooth-transport-20261023/tmp'))
for name in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG', 'KBUILD_MODPOST_WARN', 'KBUILD_MODPOST_NOFINAL']:
    env.pop(name, None)
command = ['make', '-C', str(VIEW), 'O=' + str(O), 'ARCH=arm64',
    'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'KERNELRELEASE=' + REL,
    'W=1', 'KCFLAGS=-Werror', '-j1']
for member in members:
    command += ['-o', member]
command += ['drivers/bluetooth/btbcm.ko', 'drivers/bluetooth/btqca.ko', 'drivers/bluetooth/hci_uart.ko']
old_module = pm / 'hci_uart-qca-pm-r2-k363-intree.ko'
ret, failure, abi = None, None, None
started = time.monotonic()
build_lines = []
unexpected_cc = []
restoration_errors = []
guard_errors = {}
process = None
try:
    # Break only the owned serdev source symlink before any write.
    for name in lock['candidate_sha256']:
        path = VIEW / 'drivers/bluetooth' / name
        if path.is_symlink():
            path.unlink()
        shutil.copy2(R / 'candidate' / name, path)
        assert not path.is_symlink() and sha(path) == lock['candidate_sha256'][name]
    for entry in objects['objects']:
        stem = Path(entry['path']).name.split('-static-fixes-', 1)[0]
        shutil.copy2(entry['path'], O / 'drivers/bluetooth' / (stem + '.o'))
    # Force precisely the composite relink. -o freezes the verified members.
    (O / 'drivers/bluetooth/hci_uart.o').unlink()
    with (P / 'link.log').open('x') as log:
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True)
        state = dict(terminal=False, pid=process.pid, targets=command[-3:], command=command)
        (P / 'state-private.json').write_text(json.dumps(state, indent=2) + '\n')
        print(json.dumps(state), flush=True)
        for line in process.stdout:
            log.write(line)
            log.flush()
            build_lines.append(line.rstrip())
            if re.search(r'\bCC\b', line) and not re.search(r'\b(?:hci_uart|btbcm|btqca)\.mod\.o\b', line):
                unexpected_cc.append(line.rstrip())
                os.killpg(process.pid, signal.SIGTERM)
                break
        ret = process.wait(timeout=60)
    assert ret == 0 and not unexpected_cc, ('Unexpected compilation or link failure', ret, unexpected_cc)
    diagnostics = [line for line in build_lines if 'warning:' in line.lower() or 'error:' in line.lower()]
    assert not diagnostics, diagnostics
    for entry in objects['objects']:
        stem = Path(entry['path']).name.split('-static-fixes-', 1)[0]
        assert sha(O / 'drivers/bluetooth' / (stem + '.o')) == entry['sha256']
    full = P / 'hci_uart-static-fixes-k363-intree.ko'
    stripped = P / 'hci_uart-static-fixes-k363-intree-stripped.ko'
    shutil.copy2(O / 'drivers/bluetooth/hci_uart.ko', full)
    shutil.copy2(full, stripped)
    subprocess.run(['aarch64-linux-gnu-strip', '--strip-debug', str(stripped)], check=True)
    info = lambda key, module: output(['modinfo', '-F', key, str(module)])
    expected_vermagic = info('vermagic', old_module)
    assert expected_vermagic == REL + ' SMP preempt mod_unload aarch64'
    assert info('vermagic', full) == info('vermagic', stripped) == expected_vermagic
    assert info('name', full) == info('name', stripped) == 'hci_uart'
    assert info('intree', full) == info('intree', stripped) == 'Y'
    assert info('depends', full) == info('depends', stripped) == info('depends', old_module) == 'btbcm,btqca'
    assert info('alias', full) == info('alias', old_module)
    imports = sorted({line.split()[-1] for line in output(['aarch64-linux-gnu-nm', '-u', str(full)]).splitlines()})
    original = {line.split()[1]: line.split() for line in (P / 'original363-Module.symvers').read_text().splitlines()}
    assert set(imports) <= original.keys(), sorted(set(imports) - original.keys())
    sections = output(['aarch64-linux-gnu-readelf', '-SW', str(full)])
    assert not re.search(r'\b__(?:versions|version_ext_names|version_ext_crcs)\b', sections)
    assert 'AArch64' in output(['aarch64-linux-gnu-readelf', '-h', str(full)])
    module_size = lambda module: next(line.split()[1] for line in output(
        ['aarch64-linux-gnu-nm', '-S', '--defined-only', str(module)]).splitlines() if line.split()[-1] == '__this_module')
    assert module_size(full) == module_size(old_module)
    exports = [line.split() for line in (O / 'Module.symvers').read_text().splitlines()
               if line.split()[2].endswith('/hci_uart')]
    original_exports = [fields for fields in original.values() if fields[2].endswith('/hci_uart')]
    assert {tuple(row) for row in exports} == {tuple(row) for row in original_exports}
    notes = output(['aarch64-linux-gnu-readelf', '-n', str(full)])
    build_id = re.search(r'Build ID: ([0-9a-f]+)', notes).group(1)
    assert build_id in output(['aarch64-linux-gnu-readelf', '-n', str(stripped)])
    abi = dict(name='hci_uart', intree='Y', vermagic=expected_vermagic, depends=['btbcm', 'btqca'],
        imported_symbols=len(imports), all_imports_in_original363=True,
        import_records={name: original[name] for name in imports},
        module_exports_exactly_original363=True, exported_symbols=len(exports),
        config_modversions=False, version_crc_enforcement=False, version_sections_absent=True,
        module_struct_bytes=int(module_size(full), 16), module_struct_matches_old_r2=True,
        alias_matches_old_r2=True, build_id=build_id, module_signed=False,
        full=dict(path=str(full), bytes=full.stat().st_size, sha256=sha(full)),
        stripped=dict(path=str(stripped), bytes=stripped.stat().st_size, sha256=sha(stripped)))
    (P / 'abi-private.json').write_text(json.dumps(abi, indent=2) + '\n')
except BaseException as exc:
    failure = repr(exc)
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)
finally:
    for text, record in snapshot.items():
        path = Path(text)
        try:
            if path.exists() or path.is_symlink():
                path.unlink()
            if record['symlink'] is not None:
                path.symlink_to(record['symlink'])
            elif record['existed']:
                shutil.copy2(P / record['backup'], path)
            if record['existed']:
                assert sha(path) == record['sha256']
                assert (os.readlink(path) if path.is_symlink() else None) == record['symlink']
            else:
                assert not path.exists() and not path.is_symlink()
        except BaseException as exc:
            restoration_errors.append(dict(path=text, error=repr(exc)))
    guard_errors = {str(p): [guard[str(p)], sha(p)] for p in protected if sha(p) != guard[str(p)]}
result = dict(terminal=True, exit=ret, failure=failure,
    passed=ret == 0 and failure is None and abi is not None and not restoration_errors and not guard_errors,
    seconds=round(time.monotonic() - started, 3), build_lines=build_lines, unexpected_cc=unexpected_cc,
    jobs=1, w1_werror=True, reused_validated_objects=True, candidate_sha256=lock['candidate_sha256'],
    source_lock_sha256=sha(R / 'source-lock.json'), link_script_sha256=sha(Path(__file__)),
    original_image_sha256=sha(image), original_image_config_sha256=hashlib.sha256(image_config).hexdigest(),
    original363_symvers_sha256=sha(P / 'original363-Module.symvers'), fixed_commit=lock['commit'],
    abi=abi, restoration_errors=restoration_errors, guard_errors=guard_errors,
    backed_up_paths=len(snapshot), mutable_all_restored=not restoration_errors,
    protected_inputs_unchanged=not guard_errors, old_e_artifacts_unchanged=not guard_errors,
    shared_source_or_build_written=False, sdk_accessed=False, image_built=False,
    device_ssh_winrt_radio_access=False, package_built=False, installed_or_loaded=False,
    free_bytes_after=shutil.disk_usage(ROOT).free)
(P / 'state-private.json').write_text(json.dumps(result, indent=2) + '\n')
(P / 'link-validation-private.json').write_text(json.dumps(result, indent=2) + '\n')
(R / 'converged-module-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'abi'}, indent=2), flush=True)
if abi:
    print(json.dumps({k: v for k, v in abi.items() if k != 'import_records'}, indent=2), flush=True)
raise SystemExit(0 if result['passed'] else 1)
