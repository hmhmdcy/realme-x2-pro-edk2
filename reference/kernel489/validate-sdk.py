"""Load the new core with verified existing runtime in a private SDK overlay.

No APK install, hardware capture, proxy execution, or phone access. A fixture
HOME tests actual GlobalConfiguration as UID10000, not the phone account/NSS.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import traceback
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel489')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', choices=['r1', 'r2', 'r3'], required=True)
    parser.add_argument('--blocked-only-after-r2', action='store_true')
    args = parser.parse_args()
    volume = storage.mount.mounted_build().parent
    build = json.loads((HERE / 'build-validation.json').read_bytes())
    assert build['passed'] and build['sdk_bind_unmounted']
    work = volume / ('camera489-loader-' + args.attempt)
    assert not work.exists()
    root, upper, overlay_work = [work / name for name in ['root', 'upper', 'work']]
    for path in [root, upper, overlay_work]:
        path.mkdir(parents=True)
    work.chmod(0o700)
    logs = PRIVATE / ('loader-' + args.attempt)
    assert not logs.exists()
    logs.mkdir()
    assert shutil.disk_usage(volume).free > 2 * 1024**3 + 256 * 1024**2
    assert subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
    before = {name: sha(storage.SDK / name) for name in ['lib/apk/db/installed', 'etc/apk/world']}
    report = dict(stage=489, attempt=args.attempt, passed=False, sdk_overlay_used=True,
                  apk_transaction_performed=False, phone_accessed=False, camera_manager_started=False,
                  proxy_executed=False, hardware_validated=False, installed=False,
                  phone_nss_or_home_tested=False, fixture_global_configuration_tested=False,
                  other_five_ipa_signatures_retested=False)
    reused_cases = []
    if args.blocked_only_after_r2:
        assert args.attempt == 'r3'
        prior = json.loads((HERE / 'sdk-r2-validation.json').read_bytes())
        assert not prior['passed'] and prior['sdk_overlay_unmounted'] and prior['sdk_work_slot_unbound']
        assert prior['commands'][-1] == {'label': 'probe-blocked', 'exit_code': -6}
        assert all(row['exit_code'] == 0 for row in prior['commands'][:-1])
        retained = volume / 'camera489-loader-r2/upper'
        old_probe = (retained / 'tmp/kernel489-probe/probe.cpp').read_text()
        assert old_probe.replace('!value && configuration.version() == 0',
                                 '!value && configuration.version() == 1') == (HERE / 'sdk-probe.cpp').read_text()
        assert sha(retained / 'usr/lib/libcamera.so.0.7.2') == build['normalized_core']['output_sha256']
        evidence = {}
        for label in ['cam-help', 'loader-list', 'rtld-now', 'probe-personal', 'probe-system']:
            log = PRIVATE / 'loader-r2' / (label + '.log')
            evidence[label] = sha(log)
            if label.startswith('probe-'):
                mode = label.removeprefix('probe-')
                assert ('uid=10000 config=' + mode).encode() in log.read_bytes()
                reused_cases.append({'case': mode, 'passed': True, 'uid': 10000, 'attempt': 'r2', 'reused_cached_result': True})
        report['reused_r2_successful_checks'] = evidence
        report['probe_only_change_is_blocked_default_version_assertion'] = True
    mounted = False
    compiler_output = storage.SDK / ('tmp/kernel489-probe-' + args.attempt)
    assert not compiler_output.exists() and not compiler_output.is_symlink()

    def run(arguments, label, timeout=45):
        result = subprocess.run(arguments, capture_output=True, timeout=timeout)
        (logs / (label + '.log')).write_bytes(result.stdout + result.stderr)
        report.setdefault('commands', []).append({'label': label, 'exit_code': result.returncode})
        print(json.dumps({'stage': 489, 'sdk_check': label, 'exit_code': result.returncode}), flush=True)
        assert result.returncode == 0, label + ': see retained private log'
        return result

    try:
        run(['mount', '-t', 'overlay', 'overlay', '-o',
             f'lowerdir={storage.SDK},upperdir={upper},workdir={overlay_work}', str(root)], 'mount')
        mounted = True
        package_state = json.loads(Path('/mnt/e/edk2-samurai-out/kernel475/package-state-r1-private.json').read_bytes())
        manifest = json.loads(Path('/mnt/e/edk2-samurai-out/kernel475/cohort-r2-manifest-private.json').read_bytes())
        copied = 0
        for item in package_state['inventories']:
            for relative, row in item['after_files'].items():
                source = Path(package_state['roots'][item['name']]) / relative
                destination = root / relative
                assert destination.resolve(strict=False).is_relative_to(root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if 'symlink' in row:
                    assert source.is_symlink() and os.readlink(source) == row['symlink']
                    if destination.is_symlink():
                        destination.unlink()
                    else:
                        assert not destination.exists()
                    destination.symlink_to(row['symlink'])
                else:
                    assert sha(source) == row['sha256'] and not destination.is_symlink()
                    shutil.copyfile(source, destination)
                    destination.chmod(row['mode'])
                    assert sha(destination) == row['sha256']
                copied += 1
        # The actual retained private profile is resolved, not numerically run.
        profile = next(row for row in manifest['profiles'] if row['model'] == 's5kgw1')
        profile_source = Path('/mnt/e/edk2-samurai-out/kernel475/cohort-r1/forward/profiles/s5kgw1.yaml')
        assert sha(profile_source) == profile['forward_sha256']
        profile_destination = root / profile['resolved_path'].lstrip('/')
        profile_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(profile_source, profile_destination)
        profile_destination.chmod(0o644)
        core = PRIVATE / ('build-' + build['attempt']) / 'libcamera.so.0.7.2'
        assert sha(core) == build['normalized_core']['output_sha256']
        destination = root / 'usr/lib/libcamera.so.0.7.2'
        shutil.copyfile(core, destination)
        destination.chmod(0o755)
        assert sha(destination) == sha(core)
        probe_directory = root / 'tmp/kernel489-probe'
        probe_directory.mkdir()
        probe_directory.chmod(0o755)
        shutil.copyfile(HERE / 'sdk-probe.cpp', probe_directory / 'probe.cpp')
        source_state = json.loads((HERE / 'source-state.json').read_bytes())
        with storage.sdk_candidate():
            compile_command = ['chroot', str(storage.SDK), 'g++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                '-include', '/work/libcamera/src/libcamera-v0.7.2/output/config.h',
                '-DLIBCAMERA_BASE_PRIVATE', '-I/work/libcamera/src/libcamera-v0.7.2/include',
                '-I/work/libcamera/src/libcamera-v0.7.2/output/include',
                '-I/work/libcamera/src/libcamera-v0.7.2/include/libcamera/ipa',
                '-L/work/libcamera/src/libcamera-v0.7.2/output/src/libcamera',
                '-L/work/libcamera/src/libcamera-v0.7.2/output/src/libcamera/base',
                '-Wl,-rpath-link,/work/libcamera/src/libcamera-v0.7.2/output/src/libcamera/base',
                '-x', 'c++', '-', '-lcamera', '-lcamera-base', '-ldl', '-o', '/tmp/kernel489-probe-' + args.attempt]
            process = subprocess.run(compile_command, input=(HERE / 'sdk-probe.cpp').read_bytes(), capture_output=True, timeout=90)
            (logs / 'compile-probe.log').write_bytes(process.stdout + process.stderr)
            report.setdefault('commands', []).append({'label': 'compile-probe', 'exit_code': process.returncode})
            assert process.returncode == 0, 'compile-probe: see retained private log'
            shutil.copyfile(compiler_output, probe_directory / 'probe')
            compiler_output.unlink()
        (probe_directory / 'probe').chmod(0o755)
        if not args.blocked_only_after_r2:
            run(['chroot', str(root), '/usr/bin/cam', '--help'], 'cam-help')
            result = run(['chroot', str(root), '/lib/ld-musl-aarch64.so.1', '--list', '/usr/bin/cam'], 'loader-list')
            assert b'/usr/lib/libcamera.so.0.7' in result.stdout
            code = ('import ctypes,os; paths=["/usr/lib/libcamera-base.so.0.7.2",'
                    '"/usr/lib/libcamera.so.0.7.2","/usr/lib/gstreamer-1.0/libgstlibcamera.so",'
                    '"/usr/libexec/libcamera/v4l2-compat.so","/usr/lib/libcamera/ipa/ipa_camss_vfe.so"]; '
                    'loaded=[ctypes.CDLL(p,mode=os.RTLD_NOW|os.RTLD_LOCAL) for p in paths]; print("rtld_now=5")')
            run(['chroot', str(root), '/usr/bin/python3', '-B', '-c', code], 'rtld-now')
        # A fresh private HOME fixture, never the SDK or phone's real user files.
        home = probe_directory / 'home'
        configuration = home / '.config/libcamera/configuration.yaml'
        configuration.parent.mkdir(parents=True)
        for directory in [home, home / '.config', configuration.parent]:
            directory.chmod(0o755)
            os.chown(directory, 10000, 10000)
        system = root / 'etc/libcamera/configuration.yaml'
        system.write_text('version: 1\nconfiguration:\n  kernel489_probe: system\n')
        system.chmod(0o644)
        wrapper = ('import os; os.environ.clear(); '
                   'os.environ.update(PATH="/usr/bin:/bin",HOME="/tmp/kernel489-probe/home",'
                   'USER="kernel489-fixture",LOGNAME="kernel489-fixture"); '
                   'os.setgroups([]); os.setgid(10000); os.setuid(10000); '
                   'assert os.getuid()==os.geteuid()==10000; '
                   'os.execv("/tmp/kernel489-probe/probe",["probe",MODE])')
        cases = list(reused_cases)
        modes = ['blocked'] if args.blocked_only_after_r2 else ['personal', 'system', 'blocked']
        for mode in modes:
            if mode == 'personal':
                configuration.write_text('version: 1\nconfiguration:\n  kernel489_probe: personal\n')
                configuration.chmod(0o644)
            elif mode == 'system':
                configuration.unlink()
            else:
                configuration.write_text('version: 1\nconfiguration:\n  kernel489_probe: inaccessible\n')
                configuration.chmod(0o600)
                os.chown(configuration, 0, 0)
            result = run(['chroot', str(root), '/usr/bin/python3', '-B', '-c',
                          wrapper.replace('MODE', repr(mode))], 'probe-' + mode)
            assert ('config=' + mode).encode() in result.stdout
            assert b'libcamera is not installed' not in result.stderr
            if mode == 'blocked':
                assert b'Failed to open configuration file' in result.stderr
            else:
                assert b'Failed to open configuration file' not in result.stderr
            cases.append({'case': mode, 'passed': True, 'uid': 10000, 'attempt': args.attempt})
        report.update(passed=True, copied_existing_payload_files=copied,
                      runtime_core_sha256=sha(core), arm64_core_executed=True,
                      no_build_path_branch=True, sensor_properties_and_bus_mapping_executed=True,
                      original_camss_ipa_signature_verified=True, system_profile_resolved=True,
                      system_worker_resolved=True, global_configuration_cases=cases,
                      fixture_global_configuration_tested=True,
                      loader_rtld_now_components=5, source_tree=source_state['source'])
    except BaseException:
        (logs / 'failure.txt').write_text(traceback.format_exc())
        report['failure'] = traceback.format_exc().splitlines()[-1]
    finally:
        if compiler_output.exists():
            assert compiler_output.is_file() and not compiler_output.is_symlink()
            compiler_output.unlink()
        report['compiler_temporary_file_removed'] = not compiler_output.exists()
        if mounted:
            process = subprocess.run(['umount', str(root)], capture_output=True)
            (logs / 'unmount.log').write_bytes(process.stdout + process.stderr)
            report['sdk_overlay_unmounted'] = process.returncode == 0
        else:
            report['sdk_overlay_unmounted'] = True
        report['sdk_database_and_world_unchanged'] = all(sha(storage.SDK / name) == value for name, value in before.items())
        report['sdk_work_slot_unbound'] = subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
        report['passed'] = bool(report['passed'] and report['sdk_overlay_unmounted'] and report['sdk_database_and_world_unchanged'] and report['sdk_work_slot_unbound'])
        (HERE / ('sdk-' + args.attempt + '-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
        if report['passed']:
            (HERE / 'sdk-validation.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
    assert report['passed'], 'Keep the failed attempt; inspect its private logs'


if __name__ == '__main__':
    main()
