"""Current k363/r0/r2 transaction for explicitly registered isolated roots only.

Default is a pure dry run. Never stops services, unloads modules, writes a live
root, edits APK records, or bypasses signatures/ownership. The registration and
quiescence fields are staged I/O fixtures, not evidence about a real device.
"""
from pathlib import Path
import argparse
import json
import os
import stat
import subprocess
import uuid
from hardening import HERE, load_lock, load_modules, require, sha, validate_module

NAME = 'samurai-bluetooth-k363'
MARKER = '.samurai-bluetooth-staged-root.json'


class Root:
    def __init__(self, path):
        require(path.is_absolute() and '..' not in path.parts and path != Path('/'), 'Explicit non-live absolute staged root required')
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            for part in path.parts[1:]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                os.close(fd)
                fd = nxt
            require((os.fstat(fd).st_dev, os.fstat(fd).st_ino) != (os.stat('/').st_dev, os.stat('/').st_ino), 'Live root aliases are forbidden')
        except BaseException:
            os.close(fd)
            raise
        self.fd, self.path = fd, path

    def parent(self, relative, missing=False):
        parts = relative.split('/')
        require(parts and all(p not in ['', '.', '..'] for p in parts), 'Invalid relative target')
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                try:
                    nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                except FileNotFoundError:
                    if missing:
                        os.close(fd)
                        return None, parts[-1]
                    raise
                os.close(fd)
                fd = nxt
            return fd, parts[-1]
        except BaseException:
            os.close(fd)
            raise

    def read(self, relative):
        parent, name = self.parent(relative)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            with os.fdopen(fd, 'rb') as handle:
                info = os.fstat(handle.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'Nonregular or multiply linked file refused: ' + relative)
                require(info.st_size <= 8 * 1024 * 1024, 'Unexpected staged file size')
                return handle.read()
        finally:
            os.close(parent)

    def check_path(self, relative):
        parent, name = self.parent(relative, True)
        if parent is None:
            return
        try:
            try:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                return
            require(not stat.S_ISLNK(info.st_mode) and (not stat.S_ISREG(info.st_mode) or info.st_nlink == 1), 'Symlink/hardlink target refused: ' + relative)
        finally:
            os.close(parent)

    def restore(self, relative, data, expected_current):
        parent, name = self.parent(relative)
        temporary = '.samurai-r0-' + uuid.uuid4().hex
        try:
            require(sha(self.read(relative)) == expected_current, 'Target changed before restore')
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644, dir_fd=parent)
            with os.fdopen(fd, 'wb') as handle:
                handle.write(data)
                handle.flush()
                os.fchmod(handle.fileno(), 0o644)
                os.fchown(handle.fileno(), 0, 0)
                os.fsync(handle.fileno())
            require(sha(self.read(relative)) == expected_current, 'Target changed during restore')
            os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            os.fsync(parent)
        finally:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            os.close(parent)


def database(raw):
    records, owners = {}, {}
    for entry in raw.decode().split('\n\n'):
        fields, directory = {}, ''
        names = []
        for line in entry.splitlines():
            if len(line) < 2 or line[1] != ':':
                continue
            key, value = line[0], line[2:]
            if key == 'F':
                directory = value
            elif key == 'R':
                names.append(directory + '/' + value)
            elif key in ['P', 'V', 'f']:
                fields[key] = value
        if 'P' in fields:
            require(fields['P'] not in records, 'Duplicate APK record')
            records[fields['P']] = fields
            for name in names:
                require(name not in owners, 'Multiple file owners')
                owners[name] = fields['P']
    require(NAME in records, 'The staged root has not adopted the r0 package')
    return records[NAME], owners


def execute(args):
    require(os.name == 'posix' and os.geteuid() == 0, 'Use Linux and an isolated root')
    root = Root(args.root)
    calls = []
    lock = load_lock()
    candidate = json.loads((HERE / 'candidate-r2-lock.json').read_text())
    baseline = next(r for r in lock['modules'] if r['name'] == 'hci_uart')
    artifacts = json.loads((HERE / 'artifact-manifest.json').read_text())['packages']
    packages = {r['package']: r for r in artifacts}
    root_lock = None
    try:
        marker = json.loads(root.read(MARKER))
        identity = os.fstat(root.fd)
        require(marker['kind'] == 'isolated-apk-fixture' and marker['root_dev'] == identity.st_dev and marker['root_ino'] == identity.st_ino, 'Unregistered or different staged root')
        require(marker['release'] == lock['release'] and marker['compatible'] == 'realme,samurai', 'Wrong staged kernel/device identity')
        require(marker['bluetoothd_query_status'] == 1 and marker['hci_uart_loaded'] is False, 'Bluetooth must already be quiesced; this tool cannot stop it')
        root.check_path('proc/sys/kernel/random/boot_id')
        root.check_path('sys/module/hci_uart')
        require(not (root.path / 'proc/sys/kernel/random/boot_id').exists(), 'Live proc mount refused')
        require(not (root.path / 'sys/module/hci_uart').exists(), 'Loaded module fixture refused')
        record, owners = database(root.read('lib/apk/db/installed'))
        flags = record.get('f', '')
        require(set(flags) <= {'s', 'S'}, 'Unrecognized APK broken-file state')
        broken_script = 's' in flags
        actual = {}
        for module in lock['modules']:
            require(owners.get(module['target']) == NAME, 'Wrong module file owner')
            raw = root.read(module['target'])
            expected = module
            if module['name'] == 'hci_uart' and sha(raw) == candidate['module_sha256']:
                expected = dict(module, sha256=candidate['module_sha256'], bytes=candidate['module_bytes'])
            validate_module(raw, expected, lock)
            actual[module['name']] = sha(raw)
        require(record['V'] in ['0.1.0-r0', '0.1.0-r2'], 'Unrecognized package version')
        r0_bytes = actual['hci_uart'] == baseline['sha256']
        if args.action == 'upgrade':
            require(record['V'] == '0.1.0-r0' and r0_bytes and not broken_script, 'Upgrade requires a clean r0 database and payload')
        elif args.action in ['restore-bytes', 'rollback']:
            require(record['V'] == '0.1.0-r2', 'Rollback requires r2 metadata; broken r0 needs explicit repair-r0')
        else:
            require(record['V'] == '0.1.0-r0' and r0_bytes and broken_script, 'repair-r0 only accepts the observed broken-script r0 state')
        # Check all APK target ancestors before invoking even read-only APK.
        for package, version in [(args.r0_apk, '0.1.0-r0'), (args.r2_apk, '0.1.0-r2')]:
            item = packages[NAME + '-' + version + '.apk']
            require(sha(package.read_bytes()) == item['sha256'], 'Signed APK differs from frozen artifact')
            manifest = json.loads((package.parent / 'package-manifest.json').read_text())
            for target in manifest['files']:
                root.check_path(target)
        for target in ['lib/apk/db/installed', 'lib/apk/db/scripts.tar', 'etc/apk/world']:
            root.check_path(target)
        modules = load_modules(args.module_archive, lock)
        plan = dict(action=args.action, staged_root=str(args.root), before_version=record['V'], before_flags=flags, before_script_failed=broken_script,
                    before_hci_uart_sha256=actual['hci_uart'], pure_dry_run=not args.apply,
                    apk_invocations=0, apk_mutations=0, staged_process_state_is_fixture=True,
                    no_device_service_or_module_actions=True, signed_artifacts_unchanged=True)
        if not args.apply:
            return plan
        root_lock = os.open('.samurai-bluetooth-transaction.lock', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root.fd)

        def apk(command, mutation=False):
            calls.append(dict(command=command[0], mutation=mutation))
            invocation = [str(args.apk)]
            if mutation:
                # Keep the already checked directory inode as the APK root even
                # if its pathname is renamed after validation.
                invocation += ['--root', '/proc/self/fd/' + str(root.fd), '--arch', 'aarch64', '--no-network']
            invocation += ['--keys-dir', str(args.verification_keys), *map(str, command)]
            result = subprocess.run(invocation, capture_output=True, pass_fds=(root.fd,))
            calls[-1].update(exit=result.returncode, output=(result.stdout + result.stderr).decode(errors='replace'))
            require(result.returncode == 0, 'APK command failed; inspect actual metadata/payload, do not retry blindly: ' + json.dumps(calls[-1]))

        for package in [args.r0_apk, args.r2_apk]:
            apk(['verify', package])
        if args.action in ['upgrade', 'repair-r0']:
            apk(['add', args.r2_apk], True)
            if args.action == 'upgrade':
                wanted_version, wanted_hash = '0.1.0-r2', candidate['module_sha256']
            else:
                require(set(database(root.read('lib/apk/db/installed'))[0].get('f', '')) <= {'S'}, 'Intermediate repair still has broken flags')
        if args.action in ['restore-bytes', 'rollback', 'repair-r0']:
            current = sha(root.read(baseline['target']))
            if current != baseline['sha256']:
                require(current == candidate['module_sha256'], 'Unknown candidate before restore')
                root.restore(baseline['target'], modules['hci_uart'], current)
            if args.action != 'restore-bytes':
                apk(['add', args.r0_apk], True)
            wanted_version = '0.1.0-r2' if args.action == 'restore-bytes' else '0.1.0-r0'
            wanted_hash = baseline['sha256']
        after, after_owners = database(root.read('lib/apk/db/installed'))
        require(after['V'] == wanted_version and sha(root.read(baseline['target'])) == wanted_hash, 'Post-validation version/payload mismatch')
        if args.action != 'restore-bytes':
            require(set(after.get('f', '')) <= {'S'}, 'APK broken flag remains; recovery is not complete')
        require(all(after_owners.get(r['target']) == NAME for r in lock['modules']), 'Post-validation owner mismatch')
        for module in lock['modules']:
            if module['name'] != 'hci_uart':
                require(sha(root.read(module['target'])) == module['sha256'], 'Sibling module changed')
        return dict(plan, pure_dry_run=False, apk_invocations=len(calls), apk_mutations=sum(c['mutation'] for c in calls),
                    calls=calls, after_version=after['V'], after_flags=after.get('f', ''), after_script_failed='s' in after.get('f', ''),
                    after_hci_uart_sha256=wanted_hash, owner_version_payload_consistent=args.action != 'restore-bytes',
                    package_downgrade_pending=args.action == 'restore-bytes')
    finally:
        if root_lock is not None:
            os.close(root_lock)
            os.unlink('.samurai-bluetooth-transaction.lock', dir_fd=root.fd)
        os.close(root.fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['root', 'r0-apk', 'r2-apk', 'module-archive', 'apk', 'verification-keys']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--action', choices=['upgrade', 'restore-bytes', 'rollback', 'repair-r0'], required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(dict(passed=True, **execute(args))))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps(dict(passed=False, error=str(error), no_automatic_retry=True)))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
