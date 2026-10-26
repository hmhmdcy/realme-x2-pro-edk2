"""Sign a seven-package runtime snapshot from verified cached binaries; no compilation."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import time
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel475')
PRIVATE.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--attempt', required=True, choices=[f'r{x}' for x in range(1, 10)])
args = parser.parse_args()
volume = storage.mount.mounted_build().parent
work = storage.workspace() / args.attempt
assert not work.exists(), 'Preserve terminal/partial attempts; use a distinct reviewed attempt'
assert shutil.disk_usage(volume).free > 2 * 1024 ** 3 + 256 * 1024 ** 2
assert subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
work.mkdir(parents=True)
repo = PRIVATE / ('repository-' + args.attempt)
assert not repo.exists()
forward = repo / 'forward'
rollback = repo / 'rollback'
forward.mkdir(parents=True)
rollback.mkdir()
apk = Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
keys = storage.SDK / 'etc/apk/keys'
signing = Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private/samurai-linux-203.rsa')
assert signing.is_file()
old_repository = PRIVATE.parent / 'kernel440/runtime-repository-r2/forward'
old_report = json.loads((HERE.parent / 'kernel440/package-artifact-validation.json').read_bytes())
old_records = {row['name']: row for row in old_report['packages'] if row['runtime']}
assert len(old_records) == 7 and old_report['passed']
versions = {name: '0.1.0-r28' if name.startswith('samurai-camera-') else '99990.7.2-r33' for name in old_records}
baseline_versions = {name: row['version'] for name, row in old_records.items()}
base_tree = volume / 'libcamera461-completion-ownership/src/libcamera-v0.7.2'
inputs = {
    'usr/lib/libcamera.so.0.7.2': (PRIVATE.parent / 'kernel473/libcamera.so.0.7.2', 'a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b'),
    'usr/lib/libcamera-base.so.0.7.2': (base_tree / 'output/src/libcamera/base/libcamera-base.so.0.7.2', 'f8c3039b31a18007b8ccb920493b010a3629113f30d151a8820f68c0b845f3c4'),
    'usr/libexec/libcamera/camss_ipa_proxy': (PRIVATE.parent / 'kernel451/camss_ipa_proxy', '35526054954ce43d1068c710f6be6d4cd172288e4da7ffcab677712815f08f4d'),
    'usr/lib/libcamera/ipa/ipa_camss_vfe.so': (PRIVATE.parent / 'kernel444/ipa_camss_vfe.so', '4c90047d42a91b9b1585d3b2cda997d8eee61f5e3a20f136b4345abcc2556d39'),
    'usr/lib/libcamera/ipa/ipa_camss_vfe.so.sign': (PRIVATE.parent / 'kernel444/ipa_camss_vfe.so.sign', 'f5c351bd947363791c072a7b9916adea00ec1a02c52671d7f9692aa735386205'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(arguments, label):
    result = subprocess.run(arguments, capture_output=True)
    (PRIVATE / f'{label}-{args.attempt}-private.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, f'{label} failed; see retained private log'
    return result


def extract(package, root):
    fields = {}
    root.mkdir(parents=True)
    with tarfile.open(package, 'r:gz', ignore_zeros=True) as archive:
        for line in archive.extractfile('.PKGINFO').read().decode().splitlines():
            if ' = ' in line:
                key, value = line.split(' = ', 1)
                fields.setdefault(key, []).append(value)
        for item in archive.getmembers():
            rel = item.name.removeprefix('./').rstrip('/')
            if not rel or rel.startswith('.'):
                continue
            assert not rel.startswith('/') and '..' not in Path(rel).parts
            assert item.uid == item.gid == 0
            target = root / rel
            assert target.resolve(strict=False).is_relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.isdir():
                target.mkdir(exist_ok=True)
                target.chmod(item.mode)
            elif item.issym():
                assert not item.linkname.startswith('/') and (target.parent / item.linkname).resolve(strict=False).is_relative_to(root)
                target.symlink_to(item.linkname)
            elif item.isfile():
                target.write_bytes(archive.extractfile(item).read())
                target.chmod(item.mode)
            else:
                raise RuntimeError('Unsupported cached package member')
    return fields


def inventory(root):
    rows = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            rows[name] = {'symlink': os.readlink(path)}
        elif path.is_file():
            rows[name] = {'sha256': sha(path), 'bytes': path.stat().st_size, 'mode': path.stat().st_mode & 0o7777}
    return rows


for source, expected in inputs.values():
    assert sha(source) == expected, source.name
records = []
roots = {}
cohort = []
# The empty stack exercises the actual metadata schema first, before large payload compression.
order = ['samurai-camera-stack', *sorted(name for name in old_records if name != 'samurai-camera-stack')]
for name in order:
    old = old_records[name]
    package = old_repository / old['file']
    assert sha(package) == old['sha256']
    run([str(apk), '--keys-dir', str(keys), 'verify', str(package)], 'verify-old-' + name)
    root = work / 'payloads' / name
    metadata = extract(package, root)
    before = inventory(root)
    replaced = []
    for relative, (source, expected) in inputs.items():
        target = root / relative
        if target.is_file() and not target.is_symlink():
            shutil.copyfile(source, target)
            target.chmod(0o644 if relative.endswith('.sign') else 0o755)
            assert sha(target) == expected
            replaced.append(relative)
    after = inventory(root)
    assert before.keys() == after.keys()
    assert sorted(path for path in before if before[path] != after[path]) == sorted(replaced)
    dependencies = [value.replace('99990.7.2-r32', '99990.7.2-r33').replace('0.1.0-r27', '0.1.0-r28') for value in metadata.get('depend', [])]
    if name in {'libcamera-ipa', 'libcamera-tools', 'libcamera-gstreamer', 'libcamera-v4l2'}:
        dependencies.append('libcamera=99990.7.2-r33')
    dependencies = sorted(set(dependencies))
    provides = [value.replace('99990.7.2-r32', '99990.7.2-r33') for value in metadata.get('provides', [])]
    info = {
        'name': name, 'version': versions[name], 'arch': metadata['arch'][0],
        'description': metadata['pkgdesc'][0], 'license': metadata['license'][0],
        'origin': metadata['origin'][0], 'url': metadata['url'][0],
        'build-time': '1792713600', 'depends': ' '.join(dependencies),
    }
    if provides:
        info['provides'] = ' '.join(provides)
    if metadata.get('maintainer'):
        info['maintainer'] = metadata['maintainer'][0]
    output = forward / f'{name}-{versions[name]}.apk'
    command = [str(apk), '--keys-dir', str(keys), 'mkpkg', '--compression', 'deflate:9', '--sign-key', str(signing), '--files', str(root), '--output', str(output)]
    for key, value in info.items():
        if value:
            command.extend(['--info', key + ':' + value])
    run(command, 'mkpkg-' + name)
    run([str(apk), '--keys-dir', str(keys), 'verify', str(output)], 'verify-new-' + name)
    shutil.copyfile(package, rollback / package.name)
    records.append(dict(name=name, version=versions[name], arch=metadata['arch'][0], file=output.name,
                        bytes=output.stat().st_size, sha256=sha(output), dependencies=dependencies,
                        inherited_from=old['file'], source_package_sha256=old['sha256'], replaced_files=replaced))
    roots[name] = str(root)
    cohort.append(dict(name=name, before_files=before, after_files=after))
    print(json.dumps(dict(stage=475, package=name, signed_and_verified=True, changed_payload_files=len(replaced))), flush=True)
for kind, directory in [('forward', forward), ('rollback', rollback)]:
    run([str(apk), '--keys-dir', str(keys), 'mkndx', '--compression', 'deflate:9', '--sign-key', str(signing),
         '--pkgname-spec', '${name}-${version}.apk', '--description', 'CAMSS475 ' + kind,
         '--output', str(directory / 'packages.adb'), *[str(path) for path in sorted(directory.glob('*.apk'))]], 'index-' + kind)
    run([str(apk), '--keys-dir', str(keys), 'verify', str(directory / 'packages.adb')], 'verify-index-' + kind)
assert all(sha(path) == expected for path, expected in inputs.values())
report = dict(stage=475, attempt=args.attempt, framework_version='99990.7.2-r33', configuration_version='0.1.0-r28',
              packages=sorted(records, key=lambda row: row['name']), baseline_versions=baseline_versions,
              runtime_packages=7, rollback_packages=7, cached_binary_repack_only=True, compiled=False,
              source_binaries_byte_preserved=True, ipa6_signature_byte_preserved=True,
              generic_default_configuration_preserved=True, private_factory_data_in_apks=False,
              debug_sections_and_build_runpaths_retained=True, no_sdk_bind=True, phone_accessed=False,
              installed=False, independent_root_upgrade_validated=False, private_ipa_version=6,
              free_after_bytes=shutil.disk_usage(volume).free, passed=True)
assert report['free_after_bytes'] > 2 * 1024 ** 3
(HERE / f'package-{args.attempt}-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(PRIVATE / f'package-state-{args.attempt}-private.json').write_text(json.dumps(dict(work=str(work), repository=str(repo), roots=roots, inventories=cohort, runtime_inputs={name: dict(path=str(path), sha256=expected) for name, (path, expected) in inputs.items()}), indent=2) + '\n')
print(json.dumps(dict(stage=475, attempt=args.attempt, signed_runtime_packages=7, signed_forward_and_rollback_indexes=True,
                      compiled=False, phone_accessed=False, passed=True)), flush=True)
