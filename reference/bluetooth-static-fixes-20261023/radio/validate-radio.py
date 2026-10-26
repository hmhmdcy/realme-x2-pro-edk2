"""Run the actual old/new helper in private chroots with command fault stubs.

The whole helper is sourced in an OR-list, so its load()/refresh() cannot rely
on errexit. Paths are unchanged; /proc,/sys and DMS bytes are explicit fixtures.
No original helper, platform recipe, APK, device or service is modified.
"""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess

HERE = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


WRAPPER = r'''#!/bin/sh
mktemp() {
    if [ "$1" = -d ]; then
        case "$FAIL_MODE" in query_create) return 71;; query_empty) return 0;; esac
        result=$(command mktemp "$@") || return "$?"
        if [ "$FAIL_MODE" = boot_write ]; then mkdir "$result/boot-id" || return "$?"; fi
        command printf '%s\n' "$result"
    else
        if [ "$FAIL_MODE" = pointer_create ]; then return 74; fi
        command mktemp "$@"
    fi
}
printf() {
    if [ "$FAIL_MODE" = pointer_write ] && [ -n "${pointer:-}" ] && [ "$#" = 2 ] && [ "$1" = '%s\n' ]; then return 75; fi
    command printf "$@"
}
mv() {
    if [ "$FAIL_MODE" = pointer_publish ]; then return 76; fi
    command mv "$@"
}
cat() {
    if [ "$FAIL_MODE" = cache_boot_read ]; then
        case "$1" in /proc/sys/kernel/random/boot_id|/run/samurai-radio-address/query.*/boot-id) return 77;; esac
    fi
    command cat "$@"
}
. /helper || exit "$?"
'''

DMS = r'''#!/bin/sh
printf 'DMS-%s\n' "$1" >> /trace/events
if [ "$FAIL_MODE" = dms ]; then exit 73; fi
printf '123456' > "$2/$1-mac-le.bin" || exit "$?"
if [ "$FAIL_MODE" = dms_mode ]; then chmod 644 "$2/$1-mac-le.bin"; fi
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['original', 'build-root', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(os.name == 'posix' and os.geteuid() == 0, 'Use a Linux private fixture as root')
    require(args.build_root.is_absolute() and not args.build_root.exists() and not str(args.build_root).startswith('/mnt/'), 'Fresh Linux fixture root required')
    require(not args.output.exists(), 'New report path required')
    original = args.original.read_bytes()
    candidate_path = HERE / 'usr_sbin_samurai-radio-address'
    candidate = candidate_path.read_bytes()
    subprocess.run(['/bin/dash', '-n', str(candidate_path)], check=True)
    args.build_root.mkdir(parents=True, mode=0o700)
    template = args.build_root / 'template'
    template.mkdir()
    for utility in ['dash', 'cat', 'chmod', 'mkdir', 'rmdir', 'stat', 'wc', 'mktemp', 'mv', 'tr', 'grep', 'id', 'cut']:
        origin = Path(shutil.which(utility)).resolve()
        target = template / 'bin' / ('sh' if utility == 'dash' else utility)
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(origin, target)
        target.chmod(0o755)
        result = subprocess.run(['ldd', str(origin)], capture_output=True, text=True)
        require(result.returncode == 0, 'Expected available dynamic utility')
        for library in re.findall(r'(/[^\s()]+)', result.stdout):
            destination = template / library.lstrip('/')
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists():
                shutil.copyfile(library, destination)
                destination.chmod(0o755)
    for relative, raw, mode in [
        ('proc/device-tree/compatible', b'realme,samurai\0qcom,sm8150\0', 0o644),
        ('proc/sys/kernel/random/boot_id', b'offline-radio-fixture-boot\n', 0o644),
        ('proc/uptime', b'123.0 12.0\n', 0o644),
        ('sys/class/remoteproc/remoteproc0/state', b'running\n', 0o644),
        ('usr/sbin/samurai-modem-remoteproc', b'#!/bin/sh\nprintf "/sys/class/remoteproc/remoteproc0\\n"\n', 0o755),
        ('usr/sbin/samurai-dms-mac-read', DMS.encode(), 0o755),
        ('usr/sbin/samurai-bt-address', b'#!/bin/sh\nprintf "BT-APPLY\\n" >> /trace/events\n', 0o755),
        ('wrapper', WRAPPER.encode(), 0o755),
        ('boot-id', b'PRIVATE_ROOT_SENTINEL_BOOT\n', 0o600),
        ('bt-mac-le.bin', b'PRIVATE_ROOT_SENTINEL_ID\n', 0o600),
        ('trace/events', b'', 0o600),
    ]:
        target = template / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        target.chmod(mode)

    def fixture(name, helper, kind='bt'):
        root = args.build_root / name
        shutil.copytree(template, root)
        (root / 'helper').write_bytes(helper)
        (root / 'helper').chmod(0o755)
        other = 'wlan' if kind == 'bt' else 'bt'
        lock = root / 'run/samurai-radio-address' / ('request-' + other + '.lock')
        lock.mkdir(parents=True)
        (lock / 'other-radio-sentinel').write_bytes(b'other-radio-unchanged')
        return root

    def run(root, mode, arguments=('bt',)):
        env = dict(os.environ, PATH='/bin:/usr/bin:/usr/sbin', FAIL_MODE=mode)
        result = subprocess.run(['chroot', str(root), '/bin/sh', '/wrapper', *arguments], env=env, capture_output=True)
        # Logs stay under the explicitly private fixture, not the shared source.
        with (root / 'execution.log').open('ab') as handle:
            handle.write(result.stdout + result.stderr)
        return result

    def observe(root, kind='bt'):
        base = root / 'run/samurai-radio-address'
        pointer = base / ('current-' + kind)
        events = (root / 'trace/events').read_text().splitlines()
        other = 'wlan' if kind == 'bt' else 'bt'
        return dict(root_sentinels_unchanged=(root / 'boot-id').read_bytes() == b'PRIVATE_ROOT_SENTINEL_BOOT\n'
                and (root / 'bt-mac-le.bin').read_bytes() == b'PRIVATE_ROOT_SENTINEL_ID\n',
            published_pointer=pointer.is_file(), pointer_bytes=pointer.read_bytes() if pointer.is_file() else None,
            dms_calls=sum(line.startswith('DMS-') for line in events), bt_calls=events.count('BT-APPLY'),
            other_radio_lock_unchanged=(base / ('request-' + other + '.lock') / 'other-radio-sentinel').read_bytes() == b'other-radio-unchanged',
            own_lock_released=not (base / ('request-' + kind + '.lock')).exists())

    old_root = fixture('original-query-create-control', original)
    old = run(old_root, 'query_create')
    old_state = observe(old_root)
    require(not old_state['root_sentinels_unchanged'] and old_state['dms_calls'] == 1
            and old_state['published_pointer'] and b'RADIO_ADDRESS_QUERY_VERIFIED' in old.stdout,
            'Original OR-list bug did not reproduce')
    cases = []
    for mode, expected_dms in [('query_create', 0), ('query_empty', 0), ('boot_write', 0),
                               ('dms', 1), ('dms_mode', 1), ('pointer_create', 1),
                               ('pointer_write', 1), ('pointer_publish', 1)]:
        root = fixture('candidate-' + mode, candidate)
        result = run(root, mode)
        state = observe(root)
        require(result.returncode != 0 and state['dms_calls'] == expected_dms and state['bt_calls'] == 0,
                'Failure did not stop later actions: ' + mode)
        require(state['root_sentinels_unchanged'] and not state['published_pointer']
                and state['other_radio_lock_unchanged'] and state['own_lock_released'], 'Bad pointer/root/lock state: ' + mode)
        require(b'RADIO_ADDRESS_QUERY_VERIFIED' not in result.stdout and b'RADIO_ADDRESS_CACHE_READY' not in result.stdout,
                'Failure printed a success receipt: ' + mode)
        cases.append(dict(case=mode, exit=result.returncode, dms_calls=state['dms_calls'], later_bt_calls=0,
                          root_unchanged=True, no_pointer_published=True, no_success_receipt=True,
                          other_radio_lock_preserved=True, own_lock_released=True))
    root = fixture('candidate-success-cache', candidate)
    result = run(root, 'none')
    state = observe(root)
    require(result.returncode == 0 and state['published_pointer'] and state['dms_calls'] == state['bt_calls'] == 1, 'Success failed')
    query = root / state['pointer_bytes'].decode().strip().lstrip('/')
    require(stat.S_IMODE(query.stat().st_mode) == 0o700 and stat.S_IMODE((query/'boot-id').stat().st_mode) == 0o600
            and stat.S_IMODE((query/'bt-mac-le.bin').stat().st_mode) == 0o600, 'Private query checks were not retained')
    hit = run(root, 'none')
    hit_state = observe(root)
    require(hit.returncode == 0 and hit_state['pointer_bytes'] == state['pointer_bytes'] and hit_state['dms_calls'] == 1 and hit_state['bt_calls'] == 2,
            'Cache hit re-queried or changed pointer')
    boot_failure = run(root, 'cache_boot_read')
    failed_state = observe(root)
    require(boot_failure.returncode == 77 and failed_state['pointer_bytes'] == state['pointer_bytes']
            and failed_state['dms_calls'] == 1 and failed_state['bt_calls'] == 2, 'Boot read error was falsely accepted or published')
    root = fixture('candidate-wlan-refresh', candidate, 'wlan')
    wlan = run(root, 'none', ('refresh', 'wlan'))
    wlan_state = observe(root, 'wlan')
    require(wlan.returncode == 0 and wlan_state['published_pointer'] and wlan_state['dms_calls'] == 1
            and wlan_state['other_radio_lock_unchanged'] and wlan_state['own_lock_released'], 'Separate WLAN pointer/lock failed')
    require(args.original.read_bytes() == original, 'Original helper changed')
    patch = ''.join(difflib.unified_diff(original.decode().splitlines(True), candidate.decode().splitlines(True),
        fromfile='a/linux-port/packages/samurai-platform/usr_sbin_samurai-radio-address',
        tofile='b/linux-port/packages/samurai-platform/usr_sbin_samurai-radio-address'))
    patch_path = HERE / 'radio-address-error-propagation.patch'
    require(not patch_path.exists(), 'Do not overwrite a prior patch')
    patch_path.write_text(patch)
    report = dict(schema=1, passed=True, original_helper_sha256=sha(original), candidate_helper_sha256=sha(candidate),
        validation_source_sha256=sha(Path(__file__).read_bytes()), patch_sha256=sha(patch.encode()),
        actual_full_helper_sourced_in_or_list=True, paths_not_rewritten=True,
        command_faults_and_proc_sys_identity_are_explicit_fixtures=True,
        original_query_mktemp_failure_reproduced_root_writes_dms_and_bad_publication=True,
        failure_cases=cases, success_and_same_boot_cache_hit_passed=True,
        cache_boot_read_failure_not_falsely_accepted=True, independent_wlan_refresh_pointer_and_locks_passed=True,
        original_private_modes_boot_comparison_dms_and_two_radio_locks_preserved=True,
        no_shared_source_recipe_or_signed_apk_modified=True, new_package_built_or_signed=False,
        device_ssh_winrt_service_module_or_rootfs_build_actions=False,
        native_busybox_shell_hardware_dms_and_address_application_not_tested=True)
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key:report[key] for key in ['passed','original_helper_sha256','candidate_helper_sha256',
        'original_query_mktemp_failure_reproduced_root_writes_dms_and_bad_publication','success_and_same_boot_cache_hit_passed']}))


if __name__ == '__main__':
    main()
