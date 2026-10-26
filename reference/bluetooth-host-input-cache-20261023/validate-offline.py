"""Few local path/change checks only; never call native collect/identity."""
from pathlib import Path
import argparse
import ast
import json
import os
import runpy
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-rootfs', type=Path, required=True)
    parser.add_argument('--baseline-map', type=Path, required=True)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).with_name('cache-inputs.py')
    ast.parse(source.read_text())
    api = runpy.run_path(str(source))
    require, Reader = api['require'], api['Reader']
    require(args.private_root.is_absolute() and not args.private_root.exists() and not str(args.private_root).startswith('/mnt/'), 'Fresh private Linux scratch required')
    require(not args.output.exists(), 'New report path required')
    value = json.loads(args.baseline_map.read_text())
    api['baseline']({'baseline': value})
    original_db = (args.source_rootfs / 'lib/apk/db/installed').read_bytes()
    selected, versions = api['related_paths'](original_db)
    reader = Reader(args.source_rootfs, time.monotonic() + 30)
    actual_files = {}
    try:
        aliases = reader.aliases()
        for relative in selected:
            canonical, raw, metadata = reader.read(relative, set(selected))
            actual_files[canonical] = dict(bytes=len(raw), sha256=api['sha'](raw))
        source_links = reader.links.copy()
    finally:
        reader.close()
    args.private_root.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix='only-local-', dir=args.private_root) as temporary:
        root = Path(temporary)
        require(root.resolve().is_relative_to(args.private_root.resolve()), 'Temporary path escapes private root')
        (root / 'usr/bin').mkdir(parents=True)
        target = root / 'usr/bin/kmod'
        target.write_bytes(b'local-byte-cache-fixture-A')
        (root / 'usr/bin/depmod').symlink_to('kmod')
        reader = Reader(root, time.monotonic() + 10)
        try:
            accepted = reader.read('usr/bin/depmod', {'usr/bin/depmod', 'usr/bin/kmod'})
            require(accepted[0] == 'usr/bin/kmod' and accepted[1] == target.read_bytes(), 'Registered link did not preserve actual bytes')
            (root / 'usr/bin/unknown').symlink_to('/etc/hostname')
            try:
                reader.read('usr/bin/unknown', {'usr/bin/unknown'})
            except ValueError:
                unknown_refused = True
            else:
                raise ValueError('Unknown symlink was followed')
            before = reader.read('usr/bin/kmod')
            target.write_bytes(b'local-byte-cache-fixture-B')
            after = reader.read('usr/bin/kmod')
            require(before != after and api['sha'](before[1]) != api['sha'](after[1]), 'Actual file change was not observed')
            try:
                api['normal']('usr/../outside')
            except ValueError:
                traversal_refused = True
            else:
                raise ValueError('Traversal accepted')
        finally:
            reader.close()
    require((args.source_rootfs / 'lib/apk/db/installed').read_bytes() == original_db, 'Read-only115 database changed')
    report = dict(schema=1, source_sha256=api['sha'](source.read_bytes()), validation_source_sha256=api['sha'](Path(__file__).read_bytes()),
        original363_baseline_map_verified=True, original363_modules=len(value['modules']),
        real115_registered_related_files=len(selected), real115_canonical_files=len(actual_files),
        real115_selected_symlink_chains=len(source_links), real115_selected_bytes=sum(row['bytes'] for row in actual_files.values()),
        real115_related_package_versions=versions, registered_symlink_byte_read_passed=True,
        unknown_symlink_refused=unknown_refused, traversal_refused=traversal_refused,
        actual_file_hash_and_metadata_change_detected=True,
        native_collection_identity_or_device_calls_performed=False, cache_bundle_generated=False,
        full_elf_closure_or_execution_verified=False, original115_database_unchanged=True,
        install_trigger_chroot_module_service_or_ssh_actions=False)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
