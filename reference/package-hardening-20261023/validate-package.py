"""Verify signed APK reproducibility and offline adoption/guard boundaries."""
from pathlib import Path
import argparse
import json
import os
import re
import runpy
import shutil
import subprocess
from hardening import HERE, load_lock, load_modules, require, sha, validate_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['first', 'second', 'apk', 'verification-keys', 'build-root', 'module-archive', 'legacy-module', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    require(os.geteuid() == 0 and args.build_root.is_absolute() and not args.build_root.exists(), 'Use a new isolated Linux directory as root')
    require(not str(args.build_root).startswith('/mnt/'), 'Use a Linux filesystem')
    args.build_root.mkdir(parents=True, mode=0o700)
    lock = load_lock()
    first, second = args.first.read_bytes(), args.second.read_bytes()
    require(first == second, 'Independent builds differ')

    def run(command, label, success=True):
        result = subprocess.run([str(x) for x in command], capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require((result.returncode == 0) == success, label + ' returned unexpected status')
        return result

    run([args.apk, '--keys-dir', args.verification_keys, 'verify', args.first], 'verify')
    altered = args.build_root / 'tampered.apk'
    tampered = bytearray(first)
    tampered[-10] ^= 1
    altered.write_bytes(tampered)
    run([args.apk, '--keys-dir', args.verification_keys, 'verify', altered], 'tampered-rejected', False)
    root = args.build_root / 'root'
    root.mkdir()
    manifest = json.loads((args.first.parent / 'package-manifest.json').read_text())
    require(manifest['package_sha256'] == sha(first), 'Manifest mismatch')
    # Direct APKv3 extraction has the already documented265 shared-ancestor
    # limitation. Exercise the actual package installer in the isolated root.
    modules = load_modules(args.module_archive, lock)
    for record in lock['modules']:
        path = root / record['target']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(modules[record['name']])
        path.chmod(record['mode'])
    keys = root / 'etc/apk/keys'
    keys.mkdir(parents=True)
    for key in args.verification_keys.glob('*.pub'):
        shutil.copyfile(key, keys / key.name)
    run([args.apk, '--root', root, '--initdb', '--keys-dir', keys,
         '--arch', 'aarch64', '--no-scripts', '--no-network', 'add', args.first], 'offline-adopt')
    before = {}
    for name, record in manifest['files'].items():
        path = root / name
        require(sha(path.read_bytes()) == record['sha256'], 'Extracted file differs: ' + name)
        require(path.stat().st_mode & 0o777 == record['mode'], 'Extracted mode differs: ' + name)
        require(path.stat().st_uid == 0 and path.stat().st_gid == 0, 'Extracted ownership differs')
        before[name] = sha(path.read_bytes())
    # Synthetic filesystem with real utilities and actual module bytes. Only uname
    # and device-tree identity are fixtures; no host /proc or device is exposed.
    for utility in ['sh', 'tr', 'grep', 'sha256sum']:
        origin = Path(shutil.which(utility))
        target = root / 'bin' / utility
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(origin, target)
        target.chmod(0o755)
        ldd = subprocess.check_output(['ldd', str(origin)], text=True)
        for name in re.findall(r'(/[^\s()]+)', ldd):
            lib = root / name.lstrip('/')
            lib.parent.mkdir(parents=True, exist_ok=True)
            if not lib.exists():
                shutil.copyfile(name, lib)
                lib.chmod(0o755)
    (root / 'dev').mkdir()
    (root / 'dev/null').write_bytes(b'')
    (root / 'proc/device-tree').mkdir(parents=True)
    compatible = root / 'proc/device-tree/compatible'
    compatible.write_bytes(b'realme,samurai\0qcom,sm8150\0')
    uname = root / 'bin/uname'

    def set_release(release):
        uname.write_text('#!/bin/sh\nprintf "%s\\n" "' + release + '"\n')
        uname.chmod(0o755)

    set_release(lock['release'])
    hook = runpy.run_path(str(HERE / 'build-apk.py'))['adoption_hook'](lock)
    require(sha(hook) == manifest['adoption_hook_sha256'], 'Tested hook differs from built hook')
    (root / 'guard').write_bytes(hook)
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-current-exact')
    set_release('7.3.0-rc6-rmx1931-samurai-k132+')
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-old-release-rejected', False)
    set_release(lock['release'])
    compatible.write_bytes(b'qcom,other\0')
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-wrong-device-rejected', False)
    compatible.write_bytes(b'realme,samurai\0qcom,sm8150\0')
    module_record = next(r for r in lock['modules'] if r['name'] == 'hci_uart')
    module = root / module_record['target']
    original = module.read_bytes()
    module.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-drift-rejected', False)
    module.write_bytes(original)
    legacy = args.legacy_module.read_bytes()
    legacy_record = dict(module_record, sha256=sha(legacy), bytes=len(legacy))
    try:
        validate_module(legacy, legacy_record, lock)
    except ValueError as error:
        require('Wrong kernel ABI' in str(error), 'Legacy module rejected for an unexpected reason')
    else:
        raise ValueError('Legacy k132 module accepted')
    require(all(sha((root / name).read_bytes()) == digest for name, digest in before.items()), 'Adoption changed a payload byte')
    run([args.apk, '--root', root, 'info', '-W', '/' + module_record['target']], 'offline-owner')
    report = dict(schema=1, package=manifest['package'], package_sha256=sha(first),
                  independent_signed_builds_byte_identical=True, trusted_signature_verified=True,
                  tampered_package_rejected=True, installed_files_modes_and_root_ownership_verified=True,
                  adoption_hook_exact_current_passed=True, old_release_rejected=True,
                  wrong_device_rejected=True, payload_drift_rejected=True,
                  legacy_k132_module_rejected_by_current_abi=True,
                  offline_apk_adoption_and_owner_passed=True, offline_payload_unchanged=True,
                  offline_installation_scripts_disabled=True, device_install_performed=False,
                  device_current_ownership_still_requires_window=True,
                  package_file_count=len(manifest['files']))
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
