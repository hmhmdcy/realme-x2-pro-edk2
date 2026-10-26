"""Build a signed single-program adoption package for the verified207 TFTP.

The package recipe reuses the fixed radio source lock and existing207 binary.
No modem, radio service, device or SDK operations are performed.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
from hardening import HERE, REPO, require, sha

EXPECTED = 'b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1'
TARGET = 'usr/sbin/samurai-tqftpserv'


def adoption_hook():
    return ("#!/bin/sh\nset -eu\n"
            "tr '\\0' '\\n' < /proc/device-tree/compatible | grep -qx realme,samurai || { echo WRONG_DEVICE >&2; exit 1; }\n"
            "sha256sum -c >/dev/null <<'SAMURAI_TFTP207_HASH'\n" + EXPECTED + '  /' + TARGET +
            '\nSAMURAI_TFTP207_HASH\n').encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'source-cache', 'apk', 'sign-key', 'verification-keys', 'build-root', 'output']:
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--replaces', action='append', default=[])
    args = parser.parse_args()
    require(os.name == 'posix' and os.geteuid() == 0, 'Use the isolated Linux build directory as root')
    require(args.build_root.is_absolute() and not args.build_root.exists() and not str(args.build_root).startswith('/mnt/'), 'Use a fresh Linux build directory')
    require(args.output.is_absolute() and not args.output.exists(), 'Use a fresh output directory')
    require(all(re.fullmatch('[a-z0-9][a-z0-9+_.-]*', name) for name in args.replaces), 'Invalid owner')
    data = args.candidate.read_bytes()
    require(len(data) == 922592 and sha(data) == EXPECTED, 'Not the verified207 TFTP binary')
    require(data[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', data, 18)[0] == 183, 'Expected AArch64 ELF64')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    size, count = struct.unpack_from('<HH', data, 54)
    require(size == 56 and phoff + size * count <= len(data), 'Invalid program headers')
    require(all(struct.unpack_from('<I', data, phoff + n * size)[0] != 3 for n in range(count)), 'Expected static ELF with no interpreter')
    radio = REPO / 'linux-port/radio'
    lock = json.loads((radio / 'source-lock.json').read_text())
    for name, digest in lock['own_sources'].items():
        require(sha((radio / name).read_bytes()) == digest, 'Local radio source differs: ' + name)
    for record in lock['source_records']:
        source = args.source_cache / record['repo'].split('/')[-1] / record['path']
        raw = source.read_bytes()
        # tqftpserv.c in the old build cache has already been patched. Re-read
        # the original verified source cache supplied separately to this tool.
        require(len(raw) == record['bytes'] and sha(raw) == record['sha256'], 'Upstream source cache differs: ' + record['path'])
    args.build_root.mkdir(parents=True, mode=0o700)
    args.output.mkdir(parents=True, mode=0o700)
    payload = args.build_root / 'payload'
    payload.mkdir()

    def put(name, raw, mode=0o644):
        path = payload / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(mode)

    put(TARGET, data, 0o755)
    doc = 'usr/share/doc/samurai-tftp207/'
    for name in ['source-lock.json', 'build-tftp.py', 'samurai-tftp-ram.c', 'ro-firmware.c', 'tqftpserv-work-files.patch']:
        put(doc + name, (radio / name).read_bytes())
    put(doc + 'REBUILD.md', (HERE / 'TFTP-REBUILD.md').read_bytes())
    for project in ['tqftpserv', 'qrtr']:
        put(doc + project + '-LICENSE', (args.source_cache / project / 'LICENSE').read_bytes())
    hook = args.build_root / 'adopt-tftp.pre-install'
    hook.write_bytes(adoption_hook())
    hook.chmod(0o755)
    subprocess.run(['/bin/sh', '-n', str(hook)], check=True)
    epoch = 1792713600
    files = {}
    for path in sorted(payload.rglob('*')):
        if path.is_file():
            files[str(path.relative_to(payload))] = dict(sha256=sha(path.read_bytes()), bytes=path.stat().st_size, mode=stat.S_IMODE(path.stat().st_mode))
        os.chown(path, 0, 0)
        os.utime(path, (epoch, epoch))
    os.chown(payload, 0, 0)
    os.utime(payload, (epoch, epoch))
    metadata = dict(name='samurai-tftp207', version='0.1.0-r0', arch='aarch64', license='BSD-3-Clause',
                    description='Adopt validated Realme X2 Pro RAM work-file TFTP server', origin='samurai-tftp207',
                    maintainer='Realme X2 Pro Linux port', url='https://github.com/hmhmdcy/pmaports', **{'build-time': str(epoch)})
    if args.replaces:
        metadata['replaces'] = ' '.join(sorted(set(args.replaces)))
    package = args.output / 'samurai-tftp207-0.1.0-r0.apk'
    command = [str(args.apk), 'mkpkg', '--compat', '3.0.0', '--compression', 'deflate:9', '--files', str(payload),
               '--sign-key', str(args.sign_key), '--output', str(package)]
    for key, value in sorted(metadata.items()):
        command += ['--info', key + ':' + value]
    for kind in ['pre-install', 'pre-upgrade']:
        command += ['--script', kind + ':' + str(hook)]
    for label, command in [('mkpkg', command), ('verify', [str(args.apk), '--keys-dir', str(args.verification_keys), 'verify', str(package)])]:
        result = subprocess.run(command, capture_output=True)
        (args.build_root / (label + '.log')).write_bytes(result.stdout + result.stderr)
        require(result.returncode == 0, label + ' failed')
    report = dict(schema=1, package=package.name, package_sha256=sha(package.read_bytes()), package_bytes=package.stat().st_size,
                  metadata=metadata, files=files, adoption_hook_sha256=sha(hook.read_bytes()),
                  signature_verified=True, baseline_binary207_verified=True, upstream_sources_verified=10,
                  local_radio_sources_verified=True, device_install_performed=False,
                  current_file_owner_still_requires_device_window=not bool(args.replaces),
                  current_canonical_path_still_requires_device_readback=True,
                  directory_alias_test_does_not_replace_current_owner_query=True,
                  no_service_modem_nv_or_reboot_actions=True)
    (args.output / 'package-manifest.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ['package', 'package_sha256', 'package_bytes', 'signature_verified']}))


if __name__ == '__main__':
    main()
