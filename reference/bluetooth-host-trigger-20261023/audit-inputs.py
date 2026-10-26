"""Read-only alignment audit for a future native kmod trigger fixture.

Only the selected inventory/context fields are exported. No boot identity,
address, key, APK transaction, chroot, module loader or device operation.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import struct
import subprocess
import tarfile

RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'source-rootfs', 'module-archive', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    assert args.output.is_absolute() and not args.output.exists(), 'New output file required'
    snapshots = [json.loads(path.read_text()) for path in [args.before, args.after]]
    before, after = snapshots
    inventory = before['module_installation_inventory']
    context = before['apk_transaction_context']
    assert before['release'] == after['release'] == RELEASE
    assert inventory == after['module_installation_inventory']
    assert context == after['apk_transaction_context']
    archive_bytes = args.module_archive.read_bytes()
    assert sha(archive_bytes) == 'fca01dab22b0a3917f9ce5600059d00b29aa9685381c2cd2f2e4867b9fb8f73b'
    indexes = {}
    with tarfile.open(args.module_archive) as archive:
        for name, observed in sorted(inventory['indexes'].items()):
            data = archive.extractfile('usr/lib/modules/' + RELEASE + '/' + name).read()
            saved = dict(bytes=len(data), sha256=sha(data))
            assert observed['canonical'] == '/usr/lib/modules/' + RELEASE + '/' + name
            assert observed['owner']['rc'] == 1 and not observed['owner']['out']
            indexes[name] = dict(archive=saved, snapshot=observed['file'],
                                 bytes_match=saved == observed['file'], snapshot_apk_owner=None)
    root = args.source_rootfs
    source_db = (root / 'lib/apk/db/installed').read_bytes()
    source_world = (root / 'etc/apk/world').read_bytes()
    raw_records = {next((line[2:] for line in row.splitlines() if line.startswith('P:')), ''): row
                   for row in source_db.decode().split('\n\n')}
    versions = {name: next(line[2:] for line in raw_records[name].splitlines() if line.startswith('V:'))
                for name in ['busybox', 'kmod', 'bluez', 'openrc']}
    source_context = dict(installed_database=dict(bytes=len(source_db), sha256=sha(source_db)),
                          world=dict(bytes=len(source_world), sha256=sha(source_world)))
    trigger_file = root / 'lib/apk/db/triggers'
    script_archive = root / 'lib/apk/db/scripts.tar.gz'
    scripts = {}
    with tarfile.open(script_archive) as archive:
        for entry in archive:
            if entry.isfile() and entry.name.endswith('.trigger') and any(
                    entry.name.startswith(name + '-' + versions[name] + '.') for name in ['busybox', 'kmod']):
                text = archive.extractfile(entry).read()
                name = 'busybox' if entry.name.startswith('busybox-') else 'kmod'
                assert entry.name.startswith(name + '-' + versions[name] + '.')
                checksum = next(line[2:] for line in raw_records[name].splitlines() if line.startswith('C:'))
                registration_line = next(line for line in trigger_file.read_text().splitlines()
                                         if line.split()[0] == checksum)
                assert '/lib/modules/*' in registration_line.split()[1:] and '/usr/lib/modules/*' in registration_line.split()[1:]
                scripts[name] = dict(name=entry.name, bytes=len(text), sha256=sha(text),
                                     watches_both_lib_and_usr_module_trees=True,
                                     trigger_registration_paths=registration_line.split()[1:])
                if name == 'kmod':
                    assert b'if [ -e "$i"/modules.order ]; then' in text
                    assert b'/sbin/depmod "${i#*/lib/modules/}"' in text
                    scripts[name].update(modules_order_required=True, missing_order_cleans_indexes=True)
                else:
                    assert b'"$target" = "/bin/busybox"' in text
                    scripts[name]['does_not_duplicate_kmod_depmod']=True
    assert set(scripts) == {'busybox', 'kmod'}
    needed, seen, elf = ['usr/bin/busybox', 'usr/bin/kmod', 'usr/lib/ld-musl-aarch64.so.1'], set(), []
    while needed:
        relative = needed.pop()
        path = root / relative
        actual = path.resolve()
        assert actual.is_relative_to(root.resolve()) and actual.is_file()
        if actual in seen:
            continue
        seen.add(actual)
        data = actual.read_bytes()
        assert data[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', data, 18)[0] == 183
        result = subprocess.run(['readelf', '-d', str(actual)], capture_output=True, text=True, check=True)
        libraries = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', result.stdout)
        needed.extend('usr/lib/' + name for name in libraries)
        elf.append(dict(path=str(actual.relative_to(root)), bytes=len(data), sha256=sha(data), needed=libraries))
    qemu = Path('/usr/bin/qemu-aarch64')
    registration = Path('/proc/sys/fs/binfmt_misc/qemu-aarch64').read_text()
    qemu_description = subprocess.check_output(['file', str(qemu)], text=True)
    assert 'interpreter /usr/bin/qemu-aarch64\n' in registration and 'flags: POF\n' in registration
    assert 'static-pie linked' in qemu_description
    mismatches = [name for name, row in indexes.items() if not row['bytes_match']]
    report = dict(schema=1, audit_completed=True, source_sha256=sha(Path(__file__).read_bytes()),
        snapshot_sha256=[sha(args.before.read_bytes()), sha(args.after.read_bytes())],
        snapshot_inventory_and_apk_context_stable=True, exact_kernel_release=RELEASE,
        lib_link_target=inventory['lib_symlink_target'],
        both_module_paths_canonical=inventory['lib_modules_canonical'] == inventory['usr_modules_canonical'],
        archive_sha256=sha(archive_bytes), index_comparisons=indexes,
        matching_indexes=len(indexes)-len(mismatches), mismatching_indexes=mismatches,
        current_snapshot_apk_context=context, original115_apk_context=source_context,
        original115_db_matches_snapshot=source_context['installed_database'] == context['installed_database'],
        original115_world_matches_snapshot=source_context['world'] == context['world'],
        original115_dependency_versions=versions, original115_trigger_scripts=scripts,
        original115_script_archive_sha256=sha(script_archive.read_bytes()),
        original115_trigger_registration_sha256=sha(trigger_file.read_bytes()),
        minimal_original_aarch64_elf_closure=elf,
        static_qemu_and_binfmt_registration_available=True, chroot_execution_not_attempted=True,
        snapshot_has_only_hashes_not_current_db_world_or_index_bytes=True,
        native_apk_trigger_transaction_performed=False, current_runtime_index_rollback_verified=False,
        fixture_created=False, live_apply_supported=False,
        source_rootfs_sdk_apk_and_module_artifacts_modified=False,
        device_ssh_service_module_or_reboot_actions=False,
        blockers=['Six current dep/alias/symbol index files differ from the363 archive',
            'Current APK database and world differ from the115 source metadata',
            'Current complete module byte inventory/overlay payloads and differing index bytes are absent from these snapshots',
            'Current APK trigger registration/script bytes are not captured for comparison with the115 copies'],
        archive_only_trigger_fixture_would_not_prove_current_runtime_index_rollback=True)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: report[key] for key in ['audit_completed', 'matching_indexes', 'mismatching_indexes',
        'original115_db_matches_snapshot', 'original115_world_matches_snapshot', 'native_apk_trigger_transaction_performed']}))


if __name__ == '__main__':
    main()
