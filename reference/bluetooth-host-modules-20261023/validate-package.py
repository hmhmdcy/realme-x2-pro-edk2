"""Read back two signed host-module APKs in a fresh isolated APK root.

Only the new candidate is installed in the test root. Three metadata-only
dependency fixtures satisfy the solver; they do not test dependency payloads.
No dependency trigger, device, module loader or service is invoked. Signed data
blocks are compared with originals, independently of package() staging.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import zlib


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['first', 'second', 'inputs-lock', 'bnep', 'uhid', 'apk', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(os.name == 'posix' and os.geteuid() == 0, 'Use an isolated Linux filesystem root')
    require(args.build_root.is_absolute() and not str(args.build_root).startswith('/mnt/') and not args.build_root.exists(), 'Fresh Linux validation root required')
    require(args.output.is_absolute() and not args.output.exists(), 'New report path required')
    first_bytes, second_bytes = args.first.read_bytes(), args.second.read_bytes()
    require(first_bytes == second_bytes, 'Independent signed builds differ')
    args.build_root.mkdir(parents=True, mode=0o700)

    def run(command, label):
        result = subprocess.run([str(value) for value in command], capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, label + ' failed; inspect private log')
        return result.stdout.decode()

    for label, apk_path in [('first', args.first), ('second', args.second)]:
        run([args.apk, '--keys-dir', args.verification_keys, 'verify', apk_path], 'verify-' + label)
    control = run([args.apk, '--keys-dir', args.verification_keys, 'adbdump', args.first], 'adbdump')
    require('  name: samurai-bluetooth-host-k363\n' in control and '  version: 0.1.0-r0\n' in control and '  arch: aarch64\n' in control, 'Unexpected signed identity')
    require(all(token not in control for token in ['scripts:', 'triggers:', 'replaces:']), 'Unexpected script, trigger or replaces')
    dependencies = re.search(r'^  depends:(?: #[^\n]*)?\n((?:    - .+\n)+)', control, re.M)
    require(dependencies and dependencies.group(1).splitlines() == ['    - bluez', '    - kmod', '    - openrc'], 'Unexpected signed dependencies')
    release = '7.3.0-rc6-rmx1931-samurai-k363+'
    originals = {
        'usr/lib/modules/' + release + '/kernel/net/bluetooth/bnep/bnep.ko': args.bnep.read_bytes(),
        'usr/lib/modules/' + release + '/kernel/drivers/hid/uhid.ko': args.uhid.read_bytes(),
        'usr/lib/modules-load.d/60-samurai-bluetooth-host.conf': b'bnep\nuhid\n',
    }
    lock = json.loads(args.inputs_lock.read_bytes())
    for name in ['bnep', 'uhid']:
        require(sha(getattr(args, name).read_bytes()) == lock['modules'][name]['sha256'], 'Original module lock differs')
    directory, directory_index, file_index = None, 0, 0
    files = {}
    for line in control.splitlines():
        match = re.match(r'^  - name: (.+)$', line)
        if match:
            directory_index, file_index = directory_index + 1, 0
            directory = match[1]
        match = re.match(r'^      - name: (.+)$', line)
        if match:
            file_index += 1
            files[(directory_index, file_index)] = dict(path=directory + '/' + match[1])
        for pattern, key, convert in [(r'^          mode: ([0-7]+)$', 'mode', lambda s: int(s, 8)),
                                      (r'^        size: (\d+)$', 'bytes', int),
                                      (r'^        hash: ([a-f0-9]{64})$', 'sha256', str)]:
            match = re.match(pattern, line)
            if match:
                files[(directory_index, file_index)][key] = convert(match[1])
    require(len(files) == 3 and {row['path'] for row in files.values()} == set(originals), 'Unexpected signed three-file inventory')
    require(first_bytes[:6] == b'ADBc\x01\x09', 'Expected deflate9 APKv3')
    raw = zlib.decompress(first_bytes[6:], -15)
    require(raw[:8] == b'ADB.pckg', 'Unexpected package schema')
    offset, seen = 8, set()
    while offset < len(raw):
        header = struct.unpack_from('<I', raw, offset)[0]
        length, kind = header & 0x3fffffff, header >> 30
        require(length >= 4 and offset + length <= len(raw) and kind in [0, 1, 2], 'Invalid APK data block')
        body = raw[offset + 4:offset + length]
        if kind == 2:
            key = struct.unpack_from('<II', body, 0)
            require(key in files and key not in seen, 'Duplicate or unknown payload reference')
            seen.add(key)
            row, payload = files[key], body[8:]
            require(payload == originals[row['path']] and len(payload) == row['bytes'] and sha(payload) == row['sha256'] and row['mode'] == 0o644, 'Actual signed payload/mode differs from original')
        end = offset + length
        offset = (end + 7) & ~7
        require(not any(raw[end:offset]), 'Nonzero APK block padding')
    require(offset == len(raw) and len(seen) == 3, 'Incomplete actual payload readback')
    # APKv3 native extract has the already observed shared-ancestor limitation.
    # Use the real installer without scripts in a fresh isolated root. Fixtures
    # are dependency bookkeeping only: no dependency binary or hook is tested.
    root = args.build_root / 'isolated-root'
    root.mkdir()
    db = root / 'lib/apk/db'
    db.mkdir(parents=True)
    fixture = '\n\n'.join('C:Q1' + base64.b64encode(hashlib.sha1(('fixture-' + name).encode()).digest()).decode()
        + '\nP:' + name + '\nV:0\nA:aarch64\nS:0\nI:0\nT:Metadata-only offline payload-test dependency fixture'
        for name in ['bluez', 'kmod', 'openrc']) + '\n\n'
    (db / 'installed').write_text(fixture)
    (root / 'etc/apk').mkdir(parents=True)
    (root / 'etc/apk/world').write_text('bluez\nkmod\nopenrc\n')
    run([args.apk, '--root', root, '--initdb', '--arch', 'aarch64', '--keys-dir', args.verification_keys,
         '--no-scripts', '--no-network', '--no-commit-hooks', 'add', args.first], 'isolated-install')
    actual_files = {str(path.relative_to(root)) for path in (root / 'usr').rglob('*') if path.is_file()}
    require(actual_files == set(originals) and not any(path.is_symlink() for path in root.rglob('*')), 'Unexpected extracted inventory')
    checks = []
    for relative, original in sorted(originals.items()):
        extracted = root / relative
        info = extracted.stat()
        require(extracted.read_bytes() == original and stat.S_IMODE(info.st_mode) == 0o644 and info.st_uid == info.st_gid == 0, 'Actual isolated installation bytes/mode/uid/gid differ')
        owner = run([args.apk, '--root', root, 'info', '-W', '/' + relative], 'owner-' + extracted.name)
        require('samurai-bluetooth-host-k363-0.1.0-r0' in owner, 'Unexpected isolated file owner')
        checks.append(dict(path=relative, bytes=len(original), sha256=sha(original), mode=0o644, uid=0, gid=0))
    records = [row for row in (db / 'installed').read_text().split('\n\n') if '\nP:samurai-bluetooth-host-k363\n' in '\n' + row + '\n']
    require(len(records) == 1 and '\nV:0.1.0-r0\n' in '\n' + records[0] + '\n', 'Unexpected isolated package version')
    failure_flags = re.findall(r'^f:(.*)$', records[0], re.M)
    require(not any(flag in ''.join(failure_flags) for flag in 'fsx'), 'Isolated APK failure flags present')
    require(args.first.read_bytes() == first_bytes and args.second.read_bytes() == second_bytes, 'APK changed during validation')
    report = dict(schema=1, passed=True, package=args.first.name, package_bytes=len(first_bytes),
                  package_sha256=sha(first_bytes), first_path=str(args.first), second_path=str(args.second),
                  independent_signed_builds_byte_identical=True, both_trusted_signatures_verified=True,
                  all_three_actual_signed_data_blocks_and_signed_modes_match_originals=True,
                  native_apk_install_to_fresh_isolated_root_passed=True,
                  isolated_apk_owner_and_version_verified=True, isolated_apk_failure_flags=failure_flags,
                  exact_three_files_modes_and_root_ownership_verified=True, files=checks,
                  signed_dependencies=['bluez', 'kmod', 'openrc'], no_package_scripts_triggers_or_replaces=True,
                  isolated_package_install_performed=True, device_or_original_rootfs_install_performed=False,
                  metadata_only_dependency_fixtures_used=True, dependency_payload_or_service_functionality_tested=False,
                  dependency_triggers_executed=False, isolated_install_scripts_and_commit_hooks_disabled=True,
                  modules_services_device_sdk_or_image_actions_performed=False,
                  existing_system_kmod_modules_order_trigger_boundary_not_reexecuted=True,
                  current_device_modules_order_owner_identity_manifest_and_path_layout_still_pending=True,
                  hardware_pan_uhid_and_recovery_not_tested=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    require(args.first.read_bytes() == first_bytes and args.second.read_bytes() == second_bytes, 'APK changed after report write')
    print(json.dumps({key: report[key] for key in ['passed', 'package', 'package_bytes', 'package_sha256', 'native_apk_install_to_fresh_isolated_root_passed']}))


if __name__ == '__main__':
    main()
