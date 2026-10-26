"""Stage the actual platform5-r2 package() and sign its exact nineteen files.

Only invokes install in an isolated Linux payload directory. No installation,
service hook, USB, charging, radio, camera or SDK action is performed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from hardening import REPO, require, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['apk', 'sign-key', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(os.geteuid() == 0 and args.build_root.is_absolute() and not args.build_root.exists(), 'Use a new isolated Linux directory as root')
    require(not str(args.build_root).startswith('/mnt/'), 'Use a Linux filesystem for exact modes')
    require(args.output.is_absolute() and not args.output.exists(), 'Use a new output directory')
    source = REPO / 'linux-port/packages/samurai-platform'
    recipe = (source / 'APKBUILD').read_text()
    require('pkgver=5\npkgrel=2\n' in recipe, 'Expected approved5-r2 recipe')
    dependencies = re.search(r'^depends="([^"\n]+)"$', recipe, re.M).group(1)
    require('pulseaudio-bluez' in dependencies.split(), 'Missing approved Bluetooth audio dependency')
    names = re.search(r'^source="([^"\n]+)"$', recipe, re.M).group(1).split()
    checksums = re.findall(r'^([a-f0-9]{128})  (.+)$', recipe, re.M)
    require(len(names) == 19 and len(checksums) == 19 and {n for _, n in checksums} == set(names), 'Unexpected source list')
    for digest, name in checksums:
        require(hashlib.sha512((source / name).read_bytes()).hexdigest() == digest, 'Source checksum differs: ' + name)
    install_rows = re.findall(r'install -Dm([0-7]{3}) "\$srcdir"/(\S+) "\$pkgdir"/(\S+)', recipe)
    require(len(install_rows) == 19 and {n for _, n, _ in install_rows} == set(names), 'Unexpected package() install map')
    args.build_root.mkdir(parents=True, mode=0o700)
    args.output.mkdir(parents=True, mode=0o700)
    payload, srcdir = args.build_root / 'payload', args.build_root / 'source'
    payload.mkdir()
    srcdir.mkdir()
    for name in names:
        shutil.copyfile(source / name, srcdir / name)
    recipe_file = srcdir / 'APKBUILD'
    recipe_file.write_text(recipe)
    env = dict(os.environ, srcdir=str(srcdir), pkgdir=str(payload))
    result = subprocess.run(['/bin/sh', '-c', 'set -eu; . "$1"; package', 'stage-platform', str(recipe_file)], env=env, capture_output=True)
    (args.build_root / 'package-function.log').write_bytes(result.stdout + result.stderr)
    require(result.returncode == 0, 'Actual package() failed')
    files, expected_targets = {}, set()
    for mode, name, target in install_rows:
        expected_targets.add(target)
        path = payload / target
        raw = path.read_bytes()
        require(raw == (source / name).read_bytes(), 'Staged source differs: ' + target)
        require(stat.S_IMODE(path.stat().st_mode) == int(mode, 8), 'Wrong staged mode: ' + target)
        files[target] = dict(sha256=sha(raw), bytes=len(raw), mode=int(mode, 8), source=name)
    actual = {str(p.relative_to(payload)) for p in payload.rglob('*') if p.is_file()}
    require(actual == expected_targets, 'Unexpected staging files')
    epoch = 1792713600
    for path in [*payload.rglob('*'), payload]:
        os.chown(path, 0, 0)
        os.utime(path, (epoch, epoch))
    metadata = dict(name='samurai-platform', version='5-r2', arch='aarch64', origin='samurai-platform',
                    license='LicenseRef-Local-Project', description='Realme X2 Pro platform',
                    maintainer='Realme X2 Pro Linux port', url='https://github.com/hmhmdcy/pmaports',
                    depends=dependencies, **{'build-time': str(epoch)})
    package = args.output / 'samurai-platform-5-r2.apk'
    command = [str(args.apk), 'mkpkg', '--compat', '3.0.0', '--compression', 'deflate:9', '--files', str(payload),
               '--sign-key', str(args.sign_key), '--output', str(package)]
    for key, value in sorted(metadata.items()):
        command += ['--info', key + ':' + value]
    for label, command in [('mkpkg', command), ('verify', [str(args.apk), '--keys-dir', str(args.verification_keys), 'verify', str(package)])]:
        result = subprocess.run(command, capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, label + ' failed')
    report = dict(schema=1, package=package.name, package_sha256=sha(package.read_bytes()), package_bytes=package.stat().st_size,
                  metadata=metadata, files=files, actual_recipe_package_function_executed=True,
                  recipe_sha256=sha(recipe_file.read_bytes()), all_nineteen_sources_and_modes_verified=True,
                  signature_verified=True, device_install_performed=False,
                  current_runtime_file_differences_not_queried=True,
                  includes_existing_usb_script_source_snapshot=True,
                  charging_session_runtime_changes_must_be_reconciled_before_install=True,
                  service_or_device_hooks_present=False, no_new_bluetooth_audio_acceptance=True)
    (args.output / 'package-manifest.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ['package', 'package_sha256', 'package_bytes', 'signature_verified']}))


if __name__ == '__main__':
    main()
