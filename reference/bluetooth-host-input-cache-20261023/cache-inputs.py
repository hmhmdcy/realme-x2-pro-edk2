"""Bounded read-only byte cache. Default: offline request precheck only.

Native collection requires a fresh explicit window token and exact private
handoff, then emits one tar.gz to stdout only after two matching observations.
No SSH, subprocess, installation, trigger, chroot, module or service operation.
"""
from pathlib import Path, PurePosixPath
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import stat
import sys
import tarfile
import time
import zlib

RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
BASE_SHA = 'b0b115f1061ff10b94e6fcce5f0f657c0ee688f1ebe3b07be89f44bbe0ba6530'
ARCHIVE_SHA = 'fca01dab22b0a3917f9ce5600059d00b29aa9685381c2cd2f2e4867b9fb8f73b'
MOD = 'usr/lib/modules/' + RELEASE
ALIASES = {'lib': 'usr/lib', 'bin': 'usr/bin', 'sbin': 'usr/bin', 'usr/sbin': 'bin'}
MAX_FILE, MAX_TOTAL = 16 * 1024**2, 64 * 1024**2


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def normal(path):
    require(isinstance(path, str) and path and '\\' not in path, 'Invalid guest path')
    parts = path.lstrip('/').split('/')
    require(all(part not in ['', '.', '..'] for part in parts), 'Path traversal refused')
    if parts[0] in ['lib', 'bin', 'sbin']:
        parts = ['usr', 'lib' if parts[0] == 'lib' else 'bin', *parts[1:]]
    if parts[:2] == ['usr', 'sbin']:
        parts[1] = 'bin'
    return '/'.join(parts)


def metadata(info):
    return dict(dev=info.st_dev, ino=info.st_ino, mode=stat.S_IMODE(info.st_mode), uid=info.st_uid,
                gid=info.st_gid, size=info.st_size, mtime_ns=info.st_mtime_ns, ctime_ns=info.st_ctime_ns)


class Reader:
    def __init__(self, root, deadline):
        require(root.is_absolute() and '..' not in root.parts, 'Canonical absolute read root required')
        self.fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in root.parts[1:]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
                os.close(self.fd)
                self.fd = nxt
        except BaseException:
            os.close(self.fd)
            raise
        self.deadline, self.links = deadline, {}

    def close(self):
        os.close(self.fd)

    def budget(self):
        require(time.monotonic() < self.deadline, 'Read cache deadline exhausted')

    def parent(self, relative):
        self.budget()
        parts = relative.split('/')
        require(all(part not in ['', '.', '..'] for part in parts), 'Invalid canonical path')
        fd = os.dup(self.fd)
        try:
            for part in parts[:-1]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            return fd, parts[-1]
        except BaseException:
            os.close(fd)
            raise

    def aliases(self):
        result = {}
        for path, expected in ALIASES.items():
            fd, name = self.parent(path)
            try:
                before = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(stat.S_ISLNK(before.st_mode), 'Known root alias is not a symlink: ' + path)
                target = os.readlink(name, dir_fd=fd)
                require(target == expected and metadata(os.stat(name, dir_fd=fd, follow_symlinks=False)) == metadata(before), 'Unknown or changing root alias: ' + path)
                result[path] = dict(target=target, metadata=metadata(before))
            finally:
                os.close(fd)
        return result

    def listing(self, relative):
        fd, name = self.parent(relative)
        try:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        finally:
            os.close(fd)
        try:
            rows = []
            for name in sorted(os.listdir(child)):
                require(name not in ['.', '..'] and '/' not in name, 'Invalid directory entry')
                rows.append((name, os.stat(name, dir_fd=child, follow_symlinks=False).st_mode))
            return rows
        finally:
            os.close(child)

    def read(self, path, allowed_links=frozenset()):
        current, visited = normal(path), set()
        for _ in range(12):
            self.budget()
            require(current not in visited, 'Symlink loop refused')
            visited.add(current)
            fd, name = self.parent(current)
            try:
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    require(current in allowed_links, 'Unknown symlink refused: ' + current)
                    target = os.readlink(name, dir_fd=fd)
                    require(metadata(os.stat(name, dir_fd=fd, follow_symlinks=False)) == metadata(info), 'Symlink changed while read')
                    require('\\' not in target, 'Invalid symlink spelling')
                    parts = [] if target.startswith('/') else list(PurePosixPath(current).parent.parts)
                    for component in target.split('/'):
                        if component in ['', '.']:
                            continue
                        if component == '..':
                            require(parts, 'Symlink escapes guest root')
                            parts.pop()
                        else:
                            parts.append(component)
                    destination = normal('/'.join(parts))
                    require(destination in allowed_links, 'Symlink leaves registered related-file selection')
                    self.links[current] = dict(target=target, canonical_target=destination, metadata=metadata(info))
                    current = destination
                    continue
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_FILE, 'Nonregular, linked or oversized file refused')
                source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    before = os.fstat(source)
                    require(metadata(before) == metadata(info), 'File changed before read')
                    chunks, length = [], 0
                    while True:
                        self.budget()
                        chunk = os.read(source, 128 * 1024)
                        if not chunk:
                            break
                        length += len(chunk)
                        require(length <= MAX_FILE, 'File byte budget exceeded')
                        chunks.append(chunk)
                    require(metadata(os.fstat(source)) == metadata(before), 'File changed during read')
                    return current, b''.join(chunks), metadata(before)
                finally:
                    os.close(source)
            finally:
                os.close(fd)
        raise ValueError('Symlink depth exceeded')


def related_paths(database):
    selected, directory, owner, versions = {}, '', None, {}
    library = re.compile(r'^(?:lib(?:c\.musl-aarch64|crypto|zstd|lzma|z)\.so(?:\.[A-Za-z0-9._+-]+)*|ld-musl-aarch64\.so\.1)$')
    for line in database.decode().splitlines():
        if line.startswith('P:'):
            owner = line[2:]
        elif line.startswith('V:') and owner:
            versions[owner] = line[2:]
        elif line.startswith('F:'):
            directory = line[2:]
        elif line.startswith('R:'):
            path = normal((directory + '/' + line[2:]).lstrip('/'))
            parent, name = str(PurePosixPath(path).parent), PurePosixPath(path).name
            if (parent == 'usr/bin' and name in ['busybox', 'sh', 'kmod', 'depmod']) or (parent == 'usr/lib' and library.fullmatch(name)):
                require(path not in selected or selected[path] == owner, 'Conflicting registered related-file owner')
                selected[path] = owner
    require(all('usr/bin/' + name in selected for name in ['busybox', 'sh', 'kmod', 'depmod']), 'Required registered tools missing')
    require(len(selected) <= 64, 'Related package-file budget exceeded')
    return selected, {name: versions[name] for name in set(selected.values())}


def baseline(request):
    value = request['baseline']
    require(sha(encoded(value)) == BASE_SHA and value['archive_sha256'] == ARCHIVE_SHA and value['release'] == RELEASE, 'Wrong original363 baseline map')
    require(len(value['modules']) == 778, 'Incomplete original363 map')
    return value['modules']


def identity(reader, handoff, token):
    require(handoff['window_token'] == token and isinstance(token, str) and len(token) >= 16, 'Explicit new-window confirmation required')
    require(handoff['original_transport_identity_verified'] is True, 'Original transport identity not confirmed by caller')
    require(time.time() < handoff['expires_unix'] <= time.time() + 900, 'Window expired or exceeds15 minutes')
    require(os.uname().release == RELEASE, 'Wrong current exact363 release')
    boot = reader.read('proc/sys/kernel/random/boot_id')[1]
    expected = handoff['expected_boot_id']
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', expected), 'Malformed handed-off boot identity')
    require(boot == (expected + '\n').encode(), 'Current boot differs from exact handoff')
    guard_path = handoff['original_guard_path']
    require(isinstance(guard_path, str) and guard_path.startswith('/'), 'Explicit original guard path required')
    guard = reader.read(guard_path)[1]
    require(guard == boot, 'Original guard differs from current boot')
    require(b'realme,samurai' in reader.read('sys/firmware/devicetree/base/compatible')[1].split(b'\0'), 'Wrong device compatible')
    manifest = reader.read('usr/share/samurai-charging/manifest.json')[1]
    require(sha(manifest) == handoff['charging_manifest_sha256'], 'Current manifest differs from handoff')
    return dict(boot_id=expected, original_guard_path=guard_path, guard_sha256=sha(guard), manifest_sha256=sha(manifest), release=RELEASE)


def snapshot(reader, original, keep):
    state, payload, total = {'aliases': reader.aliases(), 'files': {}, 'modules': {}}, {}, 0
    reader.links = {}

    def save(path, store=True, links=frozenset()):
        nonlocal total
        canonical, raw, info = reader.read(path, links)
        row = dict(sha256=sha(raw), bytes=len(raw), metadata=info)
        if canonical in state['files']:
            require(state['files'][canonical] == row, 'Repeated file changed during snapshot')
        state['files'][canonical] = row
        if keep and store and canonical not in payload:
            total += len(raw)
            require(total <= MAX_TOTAL, 'Private payload budget exceeded')
            payload[canonical] = raw
        return canonical, raw

    _, db = save('lib/apk/db/installed')
    save('etc/apk/world')
    save('lib/apk/db/triggers')
    save('usr/share/samurai-charging/manifest.json')
    scripts = [name for name, mode in reader.listing('usr/lib/apk/db') if name.startswith('scripts.')]
    require(scripts and set(scripts) <= {'scripts.tar', 'scripts.tar.gz'}, 'Unknown or missing actual APK script storage')
    for name in scripts:
        save('usr/lib/apk/db/' + name)
    selected, versions = related_paths(db)
    for path in sorted(selected):
        save(path, links=set(selected))
    state['related_registered_files'], state['related_package_versions'] = selected, versions
    state['elf_closure_verified_or_executed'] = False
    state['elf_scope'] = 'Registered busybox/sh/kmod/depmod and musl/crypto/zstd/lzma/z library families only; new DT_NEEDED families require offline followup'
    try:
        hooks = reader.listing('etc/apk/commit_hooks.d')
    except FileNotFoundError:
        hooks = None
    state['commit_hooks_present'] = hooks is not None
    require(hooks is None or len(hooks) <= 64, 'Commit hook count exceeded')
    for name, mode in hooks or []:
        require(stat.S_ISREG(mode), 'Unknown commit hook type refused')
        save('etc/apk/commit_hooks.d/' + name)
    all_files, walked = [], 0

    def walk(relative, depth=0):
        nonlocal walked
        require(depth <= 24, 'Module tree depth exceeded')
        for name, mode in reader.listing(relative):
            walked += 1
            require(walked <= 8192, 'Module tree entry budget exceeded')
            path = relative + '/' + name
            require(not stat.S_ISLNK(mode), 'Unknown module-tree symlink refused')
            if stat.S_ISDIR(mode):
                walk(path, depth + 1)
            else:
                require(stat.S_ISREG(mode), 'Unknown module-tree file type refused')
                require(not name.endswith(('.ko.xz', '.ko.zst', '.ko.gz')), 'Compressed module scope requires explicit followup')
                if name.endswith('.ko') or (relative == MOD and name.startswith('modules.')):
                    all_files.append(path)
    walk(MOD)
    require(MOD + '/modules.order' in all_files, 'Real modules.order missing')
    module_bytes = 0
    for path in sorted(all_files):
        if path.endswith('.ko'):
            canonical, raw, info = reader.read(path)
            relative = canonical[len(MOD) + 1:]
            row = dict(bytes=len(raw), sha256=sha(raw), metadata=info)
            state['modules'][relative] = row
            module_bytes += len(raw)
            require(len(state['modules']) <= 2048 and module_bytes <= 128 * 1024**2, 'Module byte/count budget exceeded')
            if original.get(relative) != {key: row[key] for key in ['bytes', 'sha256']}:
                state['files'][canonical] = row
                if keep:
                    total += len(raw)
                    require(total <= MAX_TOTAL, 'Overlay/private payload budget exceeded')
                    payload[canonical] = raw
        else:
            save(path)
    require(state['modules'], 'Empty actual module inventory')
    state['removed_baseline_modules'] = sorted(set(original) - set(state['modules']))
    state['selected_symlink_chains'] = reader.links.copy()
    return state, payload


def collect(request, token):
    original = baseline(request)
    seconds = request.get('max_seconds', 90)
    require(isinstance(seconds, int) and 1 <= seconds <= 120, 'Collection time budget must be1..120 seconds')
    reader = Reader(Path('/'), time.monotonic() + seconds)
    try:
        before_identity = identity(reader, request['handoff'], token)
        before, payload = snapshot(reader, original, True)
        after, _ = snapshot(reader, original, False)
        after_identity = identity(reader, request['handoff'], token)
        require(before_identity == after_identity and before == after, 'Identity, manifest or cache source changed; no valid cache emitted')
        manifest = dict(schema=1, valid=True, source='explicit-current-window-readonly-byte-cache',
            identity_private=before_identity, baseline_map_sha256=BASE_SHA, request_sha256=sha(encoded(request)),
            observed_state=before, second_observed_state_sha256=sha(encoded(after)),
            payload={path:dict(bytes=len(raw), sha256=sha(raw)) for path, raw in payload.items()},
            observation_is_not_an_atomic_apk_transaction_or_future_window_permission=True,
            installation_trigger_chroot_service_or_module_actions=False, live_apply_supported=False)
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w:gz', compresslevel=1) as archive:
            for path, raw in [('manifest.json', encoded(manifest)), *[('files/' + path, raw) for path, raw in sorted(payload.items())]]:
                reader.budget()
                member = tarfile.TarInfo(path)
                member.size, member.mode, member.mtime = len(raw), 0o600, 0
                archive.addfile(member, io.BytesIO(raw))
        require(len(output.getbuffer()) <= 72 * 1024**2, 'Compressed byte-cache budget exceeded')
        reader.budget()
        return output.getvalue()
    finally:
        reader.close()


def verify(path):
    with path.open('rb') as source:
        raw = source.read(72 * 1024**2 + 1)
    require(len(raw) <= 72 * 1024**2, 'Compressed cache too large')
    decoder = zlib.decompressobj(31)
    decoded = decoder.decompress(raw, 80 * 1024**2 + 1)
    require(len(decoded) <= 80 * 1024**2 and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, 'Incomplete or oversized gzip cache')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(decoded), mode='r:') as archive:
        for member in archive:
            require(member.isfile() and member.name not in files and len(files) < 4096 and member.size <= MAX_TOTAL, 'Invalid cache member')
            require(member.name == 'manifest.json' or (member.name.startswith('files/') and normal(member.name[6:]) == member.name[6:]), 'Cache path escape refused')
            files[member.name] = archive.extractfile(member).read()
    manifest = json.loads(files.pop('manifest.json'))
    require(manifest['valid'] is True and manifest['baseline_map_sha256'] == BASE_SHA, 'Invalid cache manifest')
    require(sha(encoded(manifest['observed_state'])) == manifest['second_observed_state_sha256'], 'State observations differ')
    require(set(files) == {'files/' + path for path in manifest['payload']}, 'Cache member inventory differs')
    require(sum(len(raw) for raw in files.values()) <= MAX_TOTAL, 'Payload total exceeds budget')
    for path, expected in manifest['payload'].items():
        raw = files['files/' + path]
        require(expected == dict(bytes=len(raw), sha256=sha(raw)), 'Cache payload checksum differs')
    return dict(verified=True, payload_files=len(files), actual_modules=len(manifest['observed_state']['modules']),
                elf_closure_verified_or_executed=False, live_apply_supported=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', default='-', help='Private JSON request; runtime supports stdin')
    parser.add_argument('--collect-current-window', metavar='TOKEN')
    parser.add_argument('--verify-cache', type=Path)
    args = parser.parse_args()
    try:
        if args.verify_cache:
            require(not args.collect_current_window, 'Choose cache verification or collection')
            print(json.dumps(verify(args.verify_cache)))
        elif not args.collect_current_window:
            result = dict(mode='offline-precheck', device_calls=0, native_collection_performed=False, live_apply_supported=False)
            if args.request != '-':
                with Path(args.request).open('rb') as source:
                    raw_request = source.read(1024 * 1024 + 1)
                require(len(raw_request) <= 1024 * 1024, 'Private request too large')
                request = json.loads(raw_request)
                baseline(request)
                result['original363_baseline_map_verified'] = True
                result['runtime_handoff_still_requires_explicit_new_window'] = True
            print(json.dumps(result))
        else:
            require(os.name == 'posix' and os.geteuid() == 0, 'Native root required for explicitly handed-off read-only cache')
            if args.request == '-':
                data = sys.stdin.buffer.read(1024 * 1024 + 1)
            else:
                with Path(args.request).open('rb') as source:
                    data = source.read(1024 * 1024 + 1)
            require(len(data) <= 1024 * 1024, 'Private request too large')
            output = collect(json.loads(data), args.collect_current_window)
            sys.stdout.buffer.write(output)
    except Exception as error:
        print(json.dumps(dict(valid=False, error=str(error), cache_not_validated=True)), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
