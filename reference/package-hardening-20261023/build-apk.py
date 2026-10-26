"""Build a signed, deterministic adoption package from the verified k363 archive.

Never contacts the device, installs packages or runs package hooks. Build root must
be a new Linux-filesystem directory. The private signing key is never copied.
"""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import stat
import subprocess
from hardening import HERE, REPO, audit_sources, load_lock, load_modules, require, sha


def adoption_hook(lock, candidate=False):
    lines = ['#!/bin/sh', 'set -eu',
             '# Adopt the already installed k363 bytes; never switch runtime state.',
             '[ "$(uname -r)" = "' + lock['release'] + '" ] || { echo WRONG_KERNEL_RELEASE >&2; exit 1; }',
             "tr '\\0' '\\n' < /proc/device-tree/compatible | grep -qx realme,samurai || { echo WRONG_DEVICE >&2; exit 1; }"]
    if candidate:
        lines += ['test ! -d /sys/module/hci_uart || { echo HCI_UART_STILL_LOADED >&2; exit 1; }',
                  'status=0; pgrep -x bluetoothd >/dev/null 2>&1 || status=$?',
                  '[ "$status" = 1 ] || { echo BLUETOOTHD_NOT_CONFIRMED_STOPPED >&2; exit 1; }']
    lines += ["sha256sum -c >/dev/null <<'SAMURAI_K363_MODULE_HASHES'"]
    lines += [r['sha256'] + '  /' + r['target'] for r in lock['modules']]
    lines += ['SAMURAI_K363_MODULE_HASHES', '']
    return '\n'.join(lines).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['module-archive', 'apk', 'sign-key', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--replaces', action='append', default=[], help='Only after confirming the current APK file owner')
    parser.add_argument('--candidate', type=Path, help='Optional versioned transport PM module; never deployed by this tool')
    parser.add_argument('--candidate-lock', type=Path, default=HERE / 'candidate-lock.json', help='Versioned candidate provenance; r1/r2 are kept independently')
    args = parser.parse_args()
    require(os.name == 'posix' and os.geteuid() == 0, 'Use root only within the isolated Linux build directory to normalize package ownership')
    require(args.build_root.is_absolute() and not args.build_root.exists(), 'A fresh absolute build directory is required')
    require(not str(args.build_root).startswith('/mnt/'), 'Use a Linux filesystem build directory')
    require(args.output.is_absolute() and not args.output.exists(), 'A fresh output directory is required')
    require(args.sign_key.is_file() and args.verification_keys.is_dir(), 'Existing signing and verification inputs required')
    require(all(re.fullmatch('[a-z0-9][a-z0-9+_.-]*', name) for name in args.replaces), 'Invalid replacing owner package name')
    lock = load_lock()
    sources = audit_sources(lock)
    modules = load_modules(args.module_archive, lock)
    candidate_lock = None
    if args.candidate:
        candidate_lock = json.loads(args.candidate_lock.read_text())
        candidate = args.candidate.read_bytes()
        candidate_record = dict(next(r for r in lock['modules'] if r['name'] == 'hci_uart'),
                                sha256=candidate_lock['module_sha256'], bytes=candidate_lock['module_bytes'])
        from hardening import validate_module
        validate_module(candidate, candidate_record, lock)
        modules['hci_uart'] = candidate
    args.build_root.mkdir(parents=True, mode=0o700)
    args.output.mkdir(parents=True, mode=0o700)
    payload = args.build_root / 'payload'
    payload.mkdir()
    epoch = lock['package']['source_date_epoch']

    def put(relative, data, mode):
        target = payload / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(mode)

    for record in lock['modules']:
        put(record['target'], modules[record['name']], record['mode'])
    doc = 'usr/share/doc/' + lock['package']['name'] + '/'
    for name in ['source-lock.json', 'current-source-validation.json', 'REBUILD.md']:
        put(doc + name, (HERE / name).read_bytes(), 0o644)
    put(doc + 'qca-power-pulse-rx.patch', (REPO / lock['historical_repair']['patch']).read_bytes(), 0o644)
    for file in sorted((HERE / 'rebuild-sources').glob('*')):
        require(file.is_file() and file.suffix in ['.c', '.h', '.dts'], 'Unexpected archived source')
        put(doc + 'rebuild-sources/' + file.name, file.read_bytes(), 0o644)
    if candidate_lock:
        put(doc + 'candidate-lock.json', args.candidate_lock.read_bytes(), 0o644)
        put(doc + 'PM-CANDIDATE.md', (HERE / candidate_lock.get('notes', 'PM-CANDIDATE.md')).read_bytes(), 0o644)
        for source, digest in candidate_lock['sources'].items():
            data = (REPO / source).read_bytes()
            require(sha(data) == digest, 'PM source/provenance changed: ' + source)
            put(doc + 'pm-candidate/' + Path(source).name, data, 0o644)
    hook = args.build_root / 'adopt-existing.pre-install'
    hook.write_bytes(adoption_hook(lock, bool(candidate_lock)))
    hook.chmod(0o755)
    subprocess.run(['/bin/sh', '-n', str(hook)], check=True)
    manifest = {}
    for path in sorted(payload.rglob('*')):
        if path.is_file():
            manifest[str(path.relative_to(payload))] = dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size,
                                                           mode=stat.S_IMODE(path.stat().st_mode))
        os.chown(path, 0, 0)
        os.utime(path, (epoch, epoch))
    os.chown(payload, 0, 0)
    os.utime(payload, (epoch, epoch))
    metadata = dict(name=lock['package']['name'], version=candidate_lock['version'] if candidate_lock else lock['package']['version'], arch='aarch64',
                    description='Realme X2 Pro k363 Bluetooth PM candidate' if candidate_lock else 'Adopt validated Realme X2 Pro k363 Bluetooth UART modules',
                    license='GPL-2.0-only', origin=lock['package']['name'],
                    maintainer='Realme X2 Pro Linux port', url='https://github.com/hmhmdcy/pmaports',
                    **{'build-time': str(epoch)})
    if args.replaces:
        metadata['replaces'] = ' '.join(sorted(set(args.replaces)))
    archive = args.output / (metadata['name'] + '-' + metadata['version'] + '.apk')
    command = [str(args.apk), 'mkpkg', '--compat', '3.0.0', '--compression', 'deflate:9',
               '--files', str(payload), '--sign-key', str(args.sign_key), '--output', str(archive)]
    for key, value in sorted(metadata.items()):
        command += ['--info', key + ':' + value]
    for kind in ['pre-install', 'pre-upgrade']:
        command += ['--script', kind + ':' + str(hook)]
    for label, command in [('mkpkg', command), ('verify', [str(args.apk), '--keys-dir', str(args.verification_keys), 'verify', str(archive)])]:
        result = subprocess.run(command, capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, label + ' failed; inspect isolated build log')
    report = dict(schema=1, package=archive.name, metadata=metadata,
                  package_sha256=sha(archive.read_bytes()), package_bytes=archive.stat().st_size,
                  files=manifest, adoption_hook_sha256=sha(hook.read_bytes()),
                  source_files_audited=len(sources), signature_verified=True,
                  module_archive_audited=True, device_install_performed=False,
                  candidate_pm_fix=bool(candidate_lock),
                  installed_baseline_required='0.1.0-r0 payload bytes' if candidate_lock else 'same current k363 payload bytes',
                  file_owner_confirmed=bool(args.replaces),
                  owner_note='Explicit replaces selected by operator' if args.replaces else 'Await current APK owner query; unowned is also a valid result',
                  services_modules_reboot_or_depmod_not_invoked=True)
    (args.output / 'package-manifest.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ['package', 'package_sha256', 'package_bytes', 'signature_verified', 'device_install_performed']}))


if __name__ == '__main__':
    main()
