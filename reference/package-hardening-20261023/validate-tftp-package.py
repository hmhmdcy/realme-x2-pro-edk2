"""Validate the TFTP adoption APK in an isolated filesystem, without services."""
from pathlib import Path
import argparse
import json
import os
import re
import runpy
import shutil
import subprocess
from hardening import HERE, require, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['first', 'second', 'candidate', 'apk', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(os.geteuid() == 0 and args.build_root.is_absolute() and not args.build_root.exists(), 'Use a fresh isolated Linux root')
    require(not str(args.build_root).startswith('/mnt/'), 'Use a Linux filesystem')
    args.build_root.mkdir(parents=True, mode=0o700)
    require(args.first.read_bytes() == args.second.read_bytes(), 'Independent TFTP APKs differ')
    manifest = json.loads((args.first.parent / 'package-manifest.json').read_text())
    require(sha(args.first.read_bytes()) == manifest['package_sha256'], 'Package manifest mismatch')

    def run(command, label, success=True):
        result = subprocess.run([str(x) for x in command], capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require((result.returncode == 0) == success, label + ' unexpected status')

    run([args.apk, '--keys-dir', args.verification_keys, 'verify', args.first], 'verify')
    bad = bytearray(args.first.read_bytes())
    bad[-10] ^= 1
    tampered = args.build_root / 'tampered.apk'
    tampered.write_bytes(bad)
    run([args.apk, '--keys-dir', args.verification_keys, 'verify', tampered], 'tampered-rejected', False)
    root = args.build_root / 'root'
    binary = root / 'usr/sbin/samurai-tqftpserv'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(args.candidate.read_bytes())
    binary.chmod(0o755)
    baseline = sha(binary.read_bytes())
    keys = root / 'etc/apk/keys'
    keys.mkdir(parents=True)
    for key in args.verification_keys.glob('*.pub'):
        shutil.copyfile(key, keys / key.name)
    run([args.apk, '--root', root, '--initdb', '--keys-dir', keys,
         '--arch', 'aarch64', '--no-scripts', '--no-network', 'add', args.first], 'offline-adopt')
    require(sha(binary.read_bytes()) == baseline, 'Adoption changed the deployed binary')
    for name, record in manifest['files'].items():
        path = root / name
        require(sha(path.read_bytes()) == record['sha256'] and path.stat().st_mode & 0o777 == record['mode'], 'Payload mismatch')
        require(path.stat().st_uid == 0 and path.stat().st_gid == 0, 'Package ownership mismatch')
    for utility in ['sh', 'tr', 'grep', 'sha256sum']:
        source = Path(shutil.which(utility))
        target = root / 'bin' / utility
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o755)
        for name in re.findall(r'(/[^\s()]+)', subprocess.check_output(['ldd', str(source)], text=True)):
            library = root / name.lstrip('/')
            library.parent.mkdir(parents=True, exist_ok=True)
            if not library.exists():
                shutil.copyfile(name, library)
                library.chmod(0o755)
    (root / 'dev').mkdir()
    (root / 'dev/null').write_bytes(b'')
    (root / 'proc/device-tree').mkdir(parents=True)
    identity = root / 'proc/device-tree/compatible'
    identity.write_bytes(b'realme,samurai\0qcom,sm8150\0')
    hook = runpy.run_path(str(HERE / 'build-tftp-apk.py'))['adoption_hook']()
    require(sha(hook) == manifest['adoption_hook_sha256'], 'Hook differs from built artifact')
    (root / 'guard').write_bytes(hook)
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-exact')
    identity.write_bytes(b'qcom,other\0')
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-wrong-device', False)
    identity.write_bytes(b'realme,samurai\0qcom,sm8150\0')
    original = binary.read_bytes()
    binary.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    run(['chroot', root, '/bin/sh', '/guard'], 'guard-payload-drift', False)
    binary.write_bytes(original)
    run([args.apk, '--root', root, 'info', '-W', '/usr/sbin/samurai-tqftpserv'], 'owner')
    report = dict(schema=1, package=manifest['package'], package_sha256=manifest['package_sha256'],
                  independent_signed_builds_byte_identical=True, trusted_signature_verified=True,
                  tampered_package_rejected=True, offline_apk_adoption_and_owner_passed=True,
                  adopted_program_byte_unchanged=True, all_files_modes_root_ownership_verified=True,
                  adoption_hook_exact_passed=True, wrong_device_rejected=True, payload_drift_rejected=True,
                  offline_installation_scripts_disabled=True, file_count=len(manifest['files']),
                  device_install_performed=False, services_or_modem_not_started=True,
                  current_file_owner_requires_device_window=True, existing207_functionality_evidence_reused=True)
    with args.output.open('x') as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
