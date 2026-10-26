"""One new private in-tree USB ko; original284 guard, no Image/SDK/device."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError('Non-optimized interpreter required')
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = HERE
BOARD = REF / 'charging-ui-audit-20261023/usb-input-irq-board-candidate'
EXPORT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-irq-wake-module-private-01')
BASE = Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01')
OUT = Path('/home/cy122/charging-management-20261023/usb-input-irq-wake-module-01')
PAIR = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-irq-board-private-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
SOURCE_HASH = '1ad0c168874448dabd6a38121a7a6b6b73384856798cbefdefaa4b759da9e2bc'
DECODER_HASH = 'a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd'


def save(path, obj):
    with path.open('w') as stream:
        json.dump(obj, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    assert sys.argv[1:] == ['--execute'], 'Explicit --execute required'
    assert os.geteuid() == 0, 'Use Ubuntu/root and the original storage guard'
    assert not OUT.exists() and not EXPORT.exists() and not (HERE / 'ko-result.json').exists(), 'Unique output exists; do not replay'
    assert sha(AUTHOR / 'delivery.json') == '9f8882d0f700656c2ef74575ce46c87ab3c44085918336fdd6b61af077205469'
    author = json.loads((AUTHOR / 'delivery.json').read_bytes())
    for name, row in author['files'].items():
        assert sha(AUTHOR / name) == row['sha256']
    assert sha(AUTHOR / 'samurai-usb-input.c') == SOURCE_HASH
    assert sha(AUTHOR / 'samurai-usb-input-decode.h') == DECODER_HASH
    dt = json.loads((BOARD / 'dt-result.json').read_bytes())
    assert dt['passed'] and dt['only_added_node'] == '/soc@0/spmi@c440000/pmic@2/usb-input@1300'
    assert sha(PAIR / 'samurai-usb-input-irq-native-private.dtb') == dt['candidate_DTB_sha256']
    image_leaf = REF / 'charging-ui-audit-20261023/gauge-image502-notify-candidate'
    assert sha(image_leaf / 'build-result.json') == 'feb6fd2e8ef8ca380f48a6f8f88b131646a874fa1d8660c3bde83a38ec8940e6'
    image = json.loads((image_leaf / 'build-result.json').read_bytes())
    assert image['passed'] and image['build']['compatibility']['builtin_export_rows_exact_501']
    assert sha(BASE / 'result.json') == sha(image_leaf / 'build-result.json')
    assert all(sha(BASE / 'build' / name) == row['sha256'] for name, row in image['build']['outputs'].items())
    helper = REF / 'kernel284/storage.py'
    assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
    spec = importlib.util.spec_from_file_location('usb_irq_storage284', helper)
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    shared = storage.mounted_build()
    assert shared == Path('/mnt/samurai-full282/build')
    old_r7 = Path('/home/cy122/charging-management-20261023/source-float-candidate')
    tracked = [shared / name for name in ['.config', 'Module.symvers', 'vmlinux.symvers', 'vmlinux.o',
               'vmlinux', 'arch/arm64/boot/Image', 'include/generated/autoconf.h', 'include/generated/utsrelease.h']]
    tracked += [shared.parent / 'source354' / name for name in ['Makefile', 'drivers/power/supply/Makefile',
                'drivers/mfd/qcom-spmi-pmic.c', 'include/linux/power_supply.h']]
    tracked += [old_r7 / 'source-view/drivers/power/supply' / name for name in
                ['Makefile', 'samurai-usb-input.c', 'samurai-usb-input-decode.h']]
    tracked += [old_r7 / 'kbuild' / name for name in ['.config', 'Module.symvers', 'vmlinux.symvers',
                'drivers/power/supply/samurai-usb-input.o', 'drivers/power/supply/samurai-usb-input.ko',
                'drivers/power/supply/.samurai-usb-input.o.cmd']]
    tracked += [BASE / 'build' / name for name in ['.config', 'Module.symvers', 'vmlinux.symvers', 'vmlinux.o',
                'vmlinux', 'arch/arm64/boot/Image', 'include/generated/autoconf.h', 'include/generated/utsrelease.h']]
    tracked += [BASE / 'source354' / name for name in ['Makefile', 'drivers/power/supply/Makefile',
                'drivers/power/supply/bq27xxx_battery.c', 'include/linux/power_supply.h']]
    optional = {shared / 'vmlinux.symvers', old_r7 / 'kbuild/vmlinux.symvers'}
    def fingerprint(path):
        if path in optional and not path.exists() and not path.is_symlink():
            return None
        return sha(path)
    protected = {
        PAIR / 'samurai-usb-input-irq-private.ko': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko'): '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko'): '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/manifest-new.json'): '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/forward-two-files.tar.gz'): '0870e32b1c6f5a927a1480a4cd523c2804dc7f44fe1796e8adb2b0100ffc71ea',
    }
    protected[Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-irq-native-pm-link-module-private-01/samurai-usb-input-irq-native-pm-link-private.ko')] = 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'
    protected[Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-pm-notify-module-private-02/samurai-usb-input-pm-notify-private.ko')] = 'ebfcb45d436f0f08dcaf4e400ea18b18cf3bd208863de33444e76c20faab4624'
    protected[Path('/mnt/e/edk2-samurai-out/charging-management-20261023/protection-observed-2719-profile-module-private-01/samurai-gauge-protection-observed-2719-private.ko')] = 'f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e'
    protected[Path('/mnt/e/edk2-samurai-out/charging-management-20261023/protection-observed-2719-cohort-private-02/service-new.py')] = '83469a88beab16cd190793ddf65e672438d0a97aaa812b63a47b4bbb4f22472f'
    protected[Path('/mnt/e/edk2-samurai-out/charging-management-20261023/protection-observed-2719-cohort-private-02/manifest-new.json')] = '8c5b7be90c4d22ba3db418c7225894e155b2cf5257eda0a681da1136081cef3c'
    compat = Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01/compatibility-result.json')
    assert sha(compat)=='1536496f7df88d71f39be324b7081cef0ab2b405bdec38e4095106316048e71d' and json.loads(compat.read_bytes())['passed']
    for path,digest in protected.items(): assert sha(path)==digest
    note_utility = REF/'charging-oem-audit-20261023/protection-query-observer-module-candidate/build-ko.py'
    assert sha(note_utility)=='6d484f62844c4976c928ab9a6e81fee0851076a33ab188974dd06cbaf689262f'
    tracked += list(protected) + [Path(__file__), helper, note_utility]
    tracked += [AUTHOR / name for name in ['samurai-usb-input.c','samurai-usb-input-decode.h','native-pm-link.c.inc','delivery.json','test-result.json']]
    before = {str(path): fingerprint(path) for path in tracked}
    assert sha(old_r7 / 'kbuild/drivers/power/supply/samurai-usb-input.ko') == '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70'
    assert sha(BASE / 'source354/drivers/power/supply/Makefile') == '5d6a64153d6475ee5eb45ec69aceaa8f31b35a3a8b5b0dd40afc33b6a727c00f'
    OUT.mkdir(parents=True)
    source, build = OUT / 'source-view', OUT / 'kbuild'
    commands, phases = [], []
    result = {'passed': False, 'private_output': str(OUT), 'source_sha256': SOURCE_HASH,
              'decoder_sha256': DECODER_HASH, 'original284_helper_sha256': sha(helper),
              'Image502_build_receipt_sha256': sha(image_leaf / 'build-result.json'),
              'IRQ_wake_source_delivery_sha256': sha(AUTHOR / 'delivery.json'),
              'old_16_cases_reused_not_rerun': True, 'unchanged_native_link_scope_reused_not_rerun': True, 'changed_IRQ_wake10_model_groups_passed': True, 'DT_result_sha256': sha(BOARD / 'dt-result.json'),
              'before': before, 'SDK_Git_device_Image_used': False, 'builder_sha256': sha(Path(__file__))}
    try:
        source.mkdir()

        def branch(src, dst, branches):
            for path in src.iterdir():
                if path.name == '.git':
                    continue
                target = dst / path.name
                if path.name in branches:
                    target.mkdir()
                    branch(path, target, branches[path.name])
                else:
                    target.symlink_to(path, target_is_directory=path.is_dir())

        branch(BASE / 'source354', source, {'drivers': {'power': {'supply': {}}}})
        supply = source / 'drivers/power/supply'
        makefile = supply / 'Makefile'
        assert makefile.is_symlink()
        makefile.unlink()
        makefile.write_bytes((BASE / 'source354/drivers/power/supply/Makefile').read_bytes() + b'\nobj-m += samurai-usb-input.o\n')
        for name in ['samurai-usb-input.c', 'samurai-usb-input-decode.h']:
            dest = supply / name
            assert not dest.exists() and not dest.is_symlink()
            shutil.copy2(AUTHOR / name, dest)
        build.mkdir()
        for name in ['.config', 'Module.symvers', 'vmlinux.symvers']:
            shutil.copy2(BASE / 'build' / name, build / name)
        (build / 'vmlinux.o').symlink_to(BASE / 'build/vmlinux.o')
        (OUT / 'tmp').mkdir()
        env = dict(os.environ)
        for name in ['KBUILD_EXTMOD', 'KBUILD_OUTPUT', 'KCONFIG_CONFIG', 'SOURCE_DATE_EPOCH', 'KBUILD_EXTRA_SYMBOLS',
                     'KCFLAGS', 'CFLAGS_KERNEL', 'CFLAGS_MODULE', 'LDFLAGS', 'MAKEFLAGS', 'MFLAGS', 'LOCALVERSION']:
            env.pop(name, None)
        env.update(PATH='/home/cy122/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin:/home/cy122/.cargo/bin:' + env['PATH'],
                   RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai',
                   KBUILD_BUILD_VERSION='502', KBUILD_BUILD_TIMESTAMP='Tue Oct 20 03:03:47 UTC 2026', TMPDIR=str(OUT / 'tmp'))
        argv = ['make', '-C', str(source), 'O=' + str(build), 'ARCH=arm64',
                'CROSS_COMPILE=aarch64-linux-gnu-', 'LOCALVERSION=+', 'W=1', 'KCFLAGS=-Werror', '-j4']
        for target in ['modules_prepare', 'drivers/power/supply/samurai-usb-input.ko']:
            log = OUT / ('prepare.log' if target == 'modules_prepare' else 'module.log')
            command = argv + [target]
            started = time.monotonic()
            with log.open('xb') as output:
                process = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT)
                try:
                    save(OUT / 'process.json', {'pid': process.pid, 'argv': command, 'terminal': False})
                    print(json.dumps({'phase': target, 'pid': process.pid, 'started': True}), flush=True)
                finally:
                    rc = process.wait()
                output.flush()
                os.fsync(output.fileno())
            terminal = {'pid': process.pid, 'argv': command, 'terminal': True, 'returncode': rc}
            save(OUT / 'process.json', terminal)
            commands.append(terminal)
            phases.append({'target': target, 'seconds': round(time.monotonic() - started, 3),
                           'returncode': rc, 'log_sha256': sha(log)})
            print(json.dumps({'phase': target, 'returncode': rc, 'seconds': phases[-1]['seconds']}), flush=True)
            assert rc == 0, (target, rc)
        diagnostics = [{'log': log.name, 'line': line} for log in [OUT / 'prepare.log', OUT / 'module.log']
                       for line in log.read_text(errors='replace').splitlines()
                       if re.search(r'\b(?:warning|error):|undefined!', line, re.I)]
        assert not diagnostics, diagnostics
        ko = build / 'drivers/power/supply/samurai-usb-input.ko'
        output = lambda command: subprocess.check_output(command, text=True)
        modinfo = output(['modinfo', str(ko)])
        assert output(['modinfo', '-F', 'intree', str(ko)]).strip() == 'Y'
        assert output(['modinfo', '-F', 'name', str(ko)]).strip() == 'samurai_usb_input'
        release = (BASE / 'build/include/config/kernel.release').read_text().strip()
        assert release == '7.3.0-rc6-rmx1931-samurai-k363+'
        assert output(['modinfo', '-F', 'vermagic', str(ko)]).split()[0] == release
        assert output(['modinfo', '-F', 'vermagic', str(ko)]).strip() == '7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64'
        assert not output(['modinfo', '-F', 'depends', str(ko)]).strip()
        assert 'AArch64' in output(['aarch64-linux-gnu-readelf', '-h', str(ko)])
        config = lambda path: {line.split('=', 1)[0]: line.split('=', 1)[1] for line in path.read_text().splitlines() if line.startswith('CONFIG_')}
        assert config(build / '.config') == config(BASE / 'build/.config')
        assert sha(build / '.config') == sha(BASE / 'build/.config')
        assert sha(build / 'include/generated/autoconf.h') == sha(BASE / 'build/include/generated/autoconf.h')
        exported = {}
        export_path = BASE / 'build/vmlinux.symvers'
        assert sha(export_path) == '84f5fc338ea72a6d71b23da50562f89c7963af50675956d3e0aff30540df4d47'
        for line in export_path.read_text().splitlines():
            row = line.split()
            assert row[2] == 'vmlinux' and row[1] not in exported
            exported[row[1]] = row
        assert len(exported) == 15097
        undefined = output(['aarch64-linux-gnu-nm', '-u', str(ko)])
        strong, weak = set(), set()
        for line in undefined.splitlines():
            fields = line.split()
            assert len(fields) == 2 and fields[-2] in ('U','w','W','v','V')
            (strong if fields[-2] == 'U' else weak).add(fields[-1])
        assert not strong - exported.keys(), sorted(strong - exported.keys())
        import_map = {name: exported[name] for name in sorted(strong)}
        save(OUT / 'Image502-import-map.json', import_map)
        assert sha(supply / 'samurai-usb-input.c') == SOURCE_HASH
        assert sha(supply / 'samurai-usb-input-decode.h') == DECODER_HASH
        EXPORT.mkdir(mode=0o700)
        exported_ko = EXPORT / 'samurai-usb-input-irq-wake-private.ko'
        assert not exported_ko.exists()
        shutil.copy2(ko, exported_ko)
        assert sha(exported_ko) == sha(ko)
        spec = importlib.util.spec_from_file_location('frozen_note_reader',note_utility)
        util = importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
        module_note,build_id = util.note(ko.read_bytes())
        (OUT/'note.gnu.build-id').write_bytes(module_note)
        (EXPORT/'note.gnu.build-id').write_bytes(module_note)
        result.update(passed=True, module_note_sha256=hashlib.sha256(module_note).hexdigest(),GNU_build_id=build_id,
                      vermagic=output(['modinfo','-F','vermagic',str(ko)]).strip(),module_path=str(ko), exported_private_module_path=str(exported_ko),
                      module_sha256=sha(ko), module_bytes=ko.stat().st_size,
                      modinfo=modinfo, intree='Y', ELF_machine='AArch64', release=release,
                      actual_config_values_exact_Image502=True, generated_autoconf_exact_Image502=True,
                      config_sha256=sha(build / '.config'), reference_config_sha256=sha(BASE / 'build/.config'),
                      Image502_exports_sha256=sha(export_path), Image502_export_count=len(exported),
                      strong_import_count=len(strong), weak_import_count=len(weak),
                      unresolved_strong_imports=[], imports_all_from_Image502_builtin=True,
                      import_map_sha256=sha(OUT / 'Image502-import-map.json'), diagnostics=[],
                      no_module_provider_fallback=True, module_only_no_Image_link=True,
                      type_ABI_or_runtime_loading_attested=False,
                      compiler_path=shutil.which('aarch64-linux-gnu-gcc'),
                      compiler_sha256=sha(Path(shutil.which('aarch64-linux-gnu-gcc')).resolve()))
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        after = {str(path): fingerprint(path) for path in tracked}
        result.update(after=after, tracked_shared_R7_Image502_inputs_unchanged=before == after,
                      commands=commands, phases=phases)
        result['passed'] = result['passed'] and before == after
        save(OUT / 'ko-result.json', result)
        save(HERE / 'ko-result.json', result)
        print(json.dumps({key: result.get(key) for key in ['passed', 'module_sha256', 'module_bytes',
                         'strong_import_count', 'tracked_shared_R7_Image502_inputs_unchanged', 'error']}), flush=True)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--execute']: raise SystemExit(main())
    assert sys.argv[1:] in ([],['--check-local'])
    assert sha(AUTHOR/'delivery.json')=='9f8882d0f700656c2ef74575ce46c87ab3c44085918336fdd6b61af077205469'
    author=json.loads((AUTHOR/'delivery.json').read_bytes())
    for name,row in author['files'].items(): assert sha(AUTHOR/name)==row['sha256']
    assert sha(AUTHOR/'samurai-usb-input.c')==SOURCE_HASH and sha(AUTHOR/'samurai-usb-input-decode.h')==DECODER_HASH
    print(json.dumps({'passed':True,'source_only':True,'storage_or_build_accessed':False,'device_accessed':False,'output_created':False}))

