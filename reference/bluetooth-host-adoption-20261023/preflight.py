"""Read-only host-module adoption/rollback review. Live apply is disabled.

No SSH, service/module operation, APK mutation, database edit, or reboot.
--apply deliberately refuses: this reviewed entry currently produces a plan.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import stat
import struct
import subprocess
import zlib

NAME = 'samurai-bluetooth-host-k363'
VERSION = '0.1.0-r0'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
APK_SHA = '982e7aff09cb696e921b6058f5f0c6f74b06afe13ed767eda988b5ea469bec9f'
FILES = {
    'usr/lib/modules/' + RELEASE + '/kernel/net/bluetooth/bnep/bnep.ko': ('b5ad9a3f3aed3ed97cf20ec656ee997550270f3ee37f4131b655020a0be5f909', 26696),
    'usr/lib/modules/' + RELEASE + '/kernel/drivers/hid/uhid.ko': ('90694197207607ebb036157aaeab03bee5023fa68c0ccae5dd3f6de22b9cd78e', 18240),
    'usr/lib/modules-load.d/60-samurai-bluetooth-host.conf': ('50cc56e88531b1e94d9f7d13d94d5c17ec04ef65b8f7d6fba2f868d51d25847a', 10),
}
ORDER = 'usr/lib/modules/' + RELEASE + '/modules.order'
ORDER_SHA = '81507a3119cebd985936e87d10b1ccbc28677d0fca370a979521449e1dc8e81f'
MANIFEST = 'usr/share/samurai-charging/manifest.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ReadRoot:
    def __init__(self, path):
        require(path.is_absolute() and '..' not in path.parts and path.resolve() == path, 'Root must have a canonical absolute path')
        self.path = path
        require((path / 'lib').is_symlink() and os.readlink(path / 'lib') == 'usr/lib', 'Expected explicitly checked lib -> usr/lib layout')

    def canonical(self, relative):
        parts = relative.split('/')
        require(parts and all(part not in ['', '.', '..'] for part in parts), 'Invalid target path')
        if parts[0] == 'lib':
            parts = ['usr', 'lib', *parts[1:]]
        return '/'.join(parts)

    def checked(self, relative, absent_ok=False):
        result = self.path
        parts = self.canonical(relative).split('/')
        for index, part in enumerate(parts):
            result = result / part
            try:
                info = result.lstat()
            except FileNotFoundError:
                require(absent_ok, 'Required path missing: ' + relative)
                return self.path.joinpath(*parts)
            require(not stat.S_ISLNK(info.st_mode), 'Unexpected symlink: ' + relative)
            if index < len(parts) - 1:
                require(stat.S_ISDIR(info.st_mode), 'Ancestor is not a directory: ' + relative)
        return result

    def read(self, relative, limit=4 * 1024 * 1024):
        path = self.checked(relative)
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as handle:
            info = os.fstat(handle.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= limit, 'Nonregular, linked or oversized input: ' + relative)
            return handle.read()


def database(raw, root):
    records, owners = {}, {}
    for entry in raw.decode().split('\n\n'):
        fields, directory, paths = {}, '', []
        for line in entry.splitlines():
            if line.startswith('F:'):
                directory = line[2:]
            elif line.startswith('R:'):
                paths.append(root.canonical((directory + '/' + line[2:]).lstrip('/')))
            elif line[:2] in ['P:', 'V:', 'f:']:
                fields[line[0]] = line[2:]
        if 'P' not in fields:
            continue
        name = fields['P']
        require(name not in records, 'Duplicate installed package record')
        records[name] = fields
        for path in paths:
            require(path not in owners or owners[path] == name, 'Conflicting canonical APK file owners')
            owners[path] = name
    return records, owners


def signed_payload(args, calls):
    raw = args.candidate.read_bytes()
    require(len(raw) == 15171 and sha(raw) == APK_SHA, 'Candidate differs from frozen signed APK')
    manifest = json.loads(args.artifact_manifest.read_text())
    require(manifest['package_name'] == NAME and manifest['version'] == VERSION and manifest['kernel_release'] == RELEASE,
            'Unexpected artifact manifest identity')
    require(any(row['sha256'] == APK_SHA and row['bytes'] == len(raw) and row['current_valid_original'] is True for row in manifest['packages']), 'Candidate is not in current artifact manifest')

    def command(verb):
        calls.append(verb)
        result = subprocess.run([str(args.apk), '--keys-dir', str(args.verification_keys), verb, str(args.candidate)],
                                capture_output=True, timeout=10)
        require(result.returncode == 0, 'Read-only APK ' + verb + ' failed')
        return result.stdout.decode()

    command('verify')
    control = command('adbdump')
    for line in ['  name: ' + NAME, '  version: ' + VERSION, '  arch: aarch64']:
        require(line + '\n' in control, 'Unexpected signed package identity')
    require(all(token not in control for token in ['scripts:', 'triggers:', 'replaces:']), 'Candidate unexpectedly owns an installer script/trigger/replaces')
    dependencies = re.search(r'^  depends:(?: #[^\n]*)?\n((?:    - .+\n)+)', control, re.M)
    require(dependencies and dependencies.group(1).splitlines() == ['    - bluez', '    - kmod', '    - openrc'], 'Unexpected candidate dependency list')
    directory, di, fi, signed = None, 0, 0, {}
    for line in control.splitlines():
        match = re.match(r'^  - name: (.+)$', line)
        if match:
            di, fi, directory = di + 1, 0, match[1]
        match = re.match(r'^      - name: (.+)$', line)
        if match:
            fi += 1
            signed[(di, fi)] = dict(path=directory + '/' + match[1])
        for pattern, key, convert in [(r'^          mode: ([0-7]+)$', 'mode', lambda s: int(s, 8)),
                                      (r'^        size: (\d+)$', 'bytes', int), (r'^        hash: ([a-f0-9]{64})$', 'sha256', str)]:
            match = re.match(pattern, line)
            if match:
                signed[(di, fi)][key] = convert(match[1])
    require(len(signed) == 3 and {row['path'] for row in signed.values()} == set(FILES), 'Signed inventory is not the three frozen files')
    for row in signed.values():
        require((row['sha256'], row['bytes']) == FILES[row['path']] and row['mode'] == 0o644, 'Signed byte/mode record differs')
    require(raw[:6] == b'ADBc\x01\x09', 'Unexpected APK encoding')
    decoded = zlib.decompress(raw[6:], -15)
    require(decoded[:8] == b'ADB.pckg', 'Unexpected APK schema')
    offset, seen = 8, set()
    while offset < len(decoded):
        header = struct.unpack_from('<I', decoded, offset)[0]
        length, kind = header & 0x3fffffff, header >> 30
        require(length >= 4 and offset + length <= len(decoded) and kind in [0, 1, 2], 'Invalid APK block')
        body = decoded[offset + 4:offset + length]
        if kind == 2:
            key = struct.unpack_from('<II', body, 0)
            require(key in signed and key not in seen, 'Unknown/duplicate data block')
            seen.add(key)
            require((sha(body[8:]), len(body[8:])) == FILES[signed[key]['path']], 'Actual payload differs')
        end = offset + length
        offset = (end + 7) & ~7
        require(not any(decoded[end:offset]), 'Invalid APK block padding')
    require(len(seen) == 3 and offset == len(decoded), 'Missing actual payload')
    require(args.candidate.read_bytes() == raw, 'Candidate changed during read-only signature/payload checks')


def inspect(args, report):
    root = ReadRoot(args.root)
    handoff = json.loads(args.baseline_lock.read_text())
    require(handoff.get('kind') == 'current-host-module-adoption-handoff', 'A current explicit handoff lock is required')
    require(args.guard_file.is_absolute() and str(args.guard_file) == handoff['original_guard_path'], 'Guard path differs from original449 handoff')
    boot = root.read('proc/sys/kernel/random/boot_id').strip()
    require(re.fullmatch(rb'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot), 'Invalid current boot identity')
    require(root.read(str(args.guard_file).lstrip('/')).strip() == boot, 'Original boot guard differs from current boot')
    require(sha(root.read(MANIFEST)) == args.charging_manifest_sha256 == handoff['charging_manifest_sha256'], 'Current charging manifest differs from explicit handoff')
    if args.root == Path('/'):
        require(not args.fixture, 'Live root cannot be a fixture')
        release = os.uname().release
        process = subprocess.run(['pgrep', '-x', 'bluetoothd'], capture_output=True, timeout=5)
        require(process.returncode == 1, 'bluetoothd is running or quiescence is unknown; no service action is performed')
    else:
        require(args.fixture, 'A non-live root requires explicit fixture mode')
        marker = json.loads(root.read('.host-adoption-fixture.json'))
        require(marker['kind'] == 'offline-real-apk-fixture' and marker['bluetoothd_query_rc'] == 1, 'Fixture identity or quiescence not explicit')
        release = root.read('proc/sys/kernel/osrelease').decode().strip()
    require(release == RELEASE and handoff['release'] == RELEASE, 'Wrong exact363 release')
    require(b'realme,samurai' in root.read('sys/firmware/devicetree/base/compatible').split(b'\0'), 'Wrong device compatible')
    require(root.checked('sys/module').is_dir(), 'Module state directory is unavailable')
    for name in ['bnep', 'uhid']:
        require(not root.checked('sys/module/' + name, True).exists(), 'Target module is loaded or state is unknown')
    installed = root.read('lib/apk/db/installed')
    records, owners = database(installed, root)
    report['database_before_sha256'] = sha(installed)
    for name in ['bluez', 'kmod', 'openrc']:
        require(name in records and records[name]['V'] == handoff['dependencies'][name], 'Missing or changed real installed dependency: ' + name)
        require(not any(flag in records[name].get('f', '') for flag in 'fsx'), 'Installed dependency has failure flags: ' + name)
    order = root.read(ORDER)
    require(len(order) == 32289 and sha(order) == ORDER_SHA == handoff['modules_order']['sha256'] and owners.get(ORDER) == handoff['modules_order']['owner'], 'Actual installed363 modules.order byte/owner differs from fixed source or handoff')
    report['modules_order_sha256'] = sha(order)
    report['before'] = {}
    if args.action == 'adopt':
        require(NAME not in records, 'Candidate already has an installed record; inspect before adopting')
    else:
        require(NAME in records and records[NAME]['V'] == VERSION and set(records[NAME].get('f', '')) <= {'f', 'S'}, 'Rollback requires exact candidate metadata with at most known broken-file state')
        require({path for path, owner in owners.items() if owner == NAME} == set(FILES), 'Rollback package owns files outside the frozen three-file inventory')
        report['candidate_failure_flags'] = records[NAME].get('f', '')
    for relative, expected in FILES.items():
        target = root.checked(relative, True)
        owner = owners.get(relative)
        if args.action == 'adopt':
            require(not target.exists() and owner is None, 'Adoption requires the exact absent/unowned pre-state: ' + relative)
            report['before'][relative] = dict(exists=False, owner=None)
        else:
            if not target.exists():
                require('f' in records[NAME].get('f', '') and owner in [None, NAME], 'Missing rollback payload is not an observed broken-file state')
                report['before'][relative] = dict(exists=False, owner=owner, known_partial_install=True)
                continue
            data = root.read(relative)
            info = target.stat()
            require((sha(data), len(data)) == expected and owner == NAME and stat.S_IMODE(info.st_mode) == 0o644 and info.st_uid == info.st_gid == 0, 'Rollback target bytes/owner/mode/uid/gid drifted')
            report['before'][relative] = dict(exists=True, owner=owner, sha256=sha(data), bytes=len(data))
    signed_payload(args, report['readonly_apk_calls'])
    require(root.read('lib/apk/db/installed') == installed, 'Database changed during read-only preflight')
    require(root.read('proc/sys/kernel/random/boot_id').strip() == boot and
            root.read(str(args.guard_file).lstrip('/')).strip() == boot and
            sha(root.read(MANIFEST)) == args.charging_manifest_sha256 and
            root.read(ORDER) == order, 'Identity, manifest or modules.order changed during preflight')
    for relative, state in report['before'].items():
        path = root.checked(relative, True)
        require(path.exists() == state['exists'], 'Target existence changed during preflight')
        if state['exists']:
            require(sha(root.read(relative)) == state['sha256'], 'Target bytes changed during preflight')
    require(all(not root.checked('sys/module/' + name, True).exists() for name in ['bnep', 'uhid']), 'Target module state changed during preflight')
    if args.root == Path('/'):
        require(os.uname().release == RELEASE and subprocess.run(['pgrep', '-x', 'bluetoothd'],
            capture_output=True, timeout=5).returncode == 1, 'Runtime quiescence changed during preflight')
    review_prefix = [str(args.apk), '--root', str(args.root), '--arch', 'aarch64', '--no-network']
    report.update(preflight_passed=True, original_guard_matches_current_boot=True,
                  charging_manifest_sha256=args.charging_manifest_sha256, exact_release=release,
                  state_is_offline_fixture=args.fixture, live_apply_supported=False,
                  review_only_argv=review_prefix + ['add', str(args.candidate)] if args.action == 'adopt'
                    else review_prefix + ['del', NAME],
                  requires_fresh_guard_and_state_immediately_before_any_future_mutation=True,
                  requires_postvalidation_even_after_nonzero_apk_exit=True,
                  required_postvalidation=['three payload byte/mode/owner states', 'package version and f/s/x flags',
                    'all prior packages/world unchanged except the candidate', 'modules.order unchanged',
                    'native kmod indexes/trigger result and alias path layout', 'both target modules remain unloaded'],
                  review_only_rollback_argv=review_prefix + ['del', NAME],
                  rollback_only_valid_for_initial_absent_unowned_three_files=True,
                  pan_hog_runtime_acceptance_pending=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/'))
    parser.add_argument('--action', choices=['adopt', 'rollback'], default='adopt')
    parser.add_argument('--fixture', action='store_true')
    parser.add_argument('--apply', action='store_true', help='Reserved: always refuses in this live-disabled review tool')
    for name in ['baseline-lock', 'guard-file', 'candidate', 'artifact-manifest', 'apk', 'verification-keys']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--charging-manifest-sha256', required=True)
    args = parser.parse_args()
    report = dict(schema=1, preflight_passed=False, live_apply_supported=False, action=args.action,
                  readonly_apk_calls=[], apk_mutations=0, device_or_service_actions=0,
                  no_target_payload_or_database_writes=True)
    try:
        require(not args.apply, 'Live apply is disabled; review the plan and unresolved trigger/index rollback boundary')
        require(re.fullmatch('[a-f0-9]{64}', args.charging_manifest_sha256), 'Explicit current manifest SHA256 required')
        inspect(args, report)
    except Exception as error:
        report['refusal'] = str(error)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['preflight_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
