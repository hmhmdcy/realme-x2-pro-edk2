"""Read-only forensic audit of the two original platform package deliveries.

No package build, extraction, installation or overwrite. The known APKv3
deflate data blocks are decoded only after the actual APK signature verifier
passes, then all nineteen payload byte strings and signed modes are compared.
"""
from pathlib import Path
import argparse
import datetime
import json
import re
import stat
import struct
import subprocess
import zlib
from hardening import require, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['private-root', 'build-base', 'apk', 'verification-keys', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Use a new incident evidence directory')
    args.output.mkdir(parents=True, mode=0o700)
    expected_hash = '49c5b03456fab276f306d52127505190cffecc815fb2e7415aefae822cb05630'
    observations = []
    controls = {}
    for index in [1, 2]:
        name = 'platform-packages' + str(index)
        package = args.private_root / name / 'samurai-platform-5-r2.apk'
        raw = package.read_bytes()
        info = package.stat()
        row = dict(directory=name, bytes=len(raw), sha256=sha(raw),
                   mtime_utc=datetime.datetime.fromtimestamp(info.st_mtime, datetime.timezone.utc).isoformat(),
                   mtime_shanghai=datetime.datetime.fromtimestamp(info.st_mtime, datetime.timezone(datetime.timedelta(hours=8))).isoformat())
        for command in ['verify', 'adbdump']:
            result = subprocess.run([str(args.apk), '--keys-dir', str(args.verification_keys), command, str(package)], capture_output=True)
            (args.output / (name + '-' + command + '.log')).write_bytes(result.stdout + result.stderr)
            row[command + '_exit'] = result.returncode
            if command == 'adbdump' and result.returncode == 0:
                controls[index] = result.stdout.decode()
        if index == 1:
            misplaced = json.loads(raw.decode())
            require(isinstance(misplaced.get('packages'), list) and misplaced.get('schema') == 1, 'Unexpected invalid file content')
            row.update(content_type='artifact-manifest JSON miswritten over APK', json_keys=sorted(misplaced),
                       usable_apk=False, cause='Final cleanup script reused p for the last APK, then p.write_text(manifest_json)')
        else:
            require(len(raw) == 12387 and sha(raw) == expected_hash and row['verify_exit'] == 0, 'Original second copy is not the verified build')
            row['usable_apk'] = True
        observations.append(row)
    control = controls[2]
    files, directory, filename = {}, None, None
    directory_index, file_index = 0, 0
    for line in control.splitlines():
        match = re.match(r'^  - name: (.+)$', line)
        if match:
            directory_index += 1
            file_index = 0
            directory = match[1]
        match = re.match(r'^      - name: (.+)$', line)
        if match:
            file_index += 1
            filename = match[1]
            files[(directory_index, file_index)] = dict(path=directory + '/' + filename)
        match = re.match(r'^          mode: ([0-7]+)$', line)
        if match:
            files[(directory_index, file_index)]['mode'] = int(match[1], 8)
        match = re.match(r'^        size: (\d+)$', line)
        if match:
            files[(directory_index, file_index)]['bytes'] = int(match[1])
        match = re.match(r'^        hash: ([a-f0-9]{64})$', line)
        if match:
            files[(directory_index, file_index)]['sha256'] = match[1]
    require(len(files) == 19 and '    - pulseaudio-bluez\n' in control and 'scripts:' not in control, 'Unexpected signed platform inventory')
    binary = (args.private_root / 'platform-packages2/samurai-platform-5-r2.apk').read_bytes()
    require(binary[:6] == b'ADBc\x01\x09', 'Expected original deflate9 APKv3')
    raw = zlib.decompress(binary[6:], -15)
    require(raw[:8] == b'ADB.pckg', 'Unexpected uncompressed package schema')
    manifest = json.loads((args.private_root / 'platform-packages2/package-manifest.json').read_text())
    offset, seen, checks = 8, set(), []
    while offset < len(raw):
        header = struct.unpack_from('<I', raw, offset)[0]
        length, kind = header & 0x3fffffff, header >> 30
        require(length >= 4 and offset + length <= len(raw), 'Invalid block extent')
        body = raw[offset + 4:offset + length]
        if kind == 2:
            key = struct.unpack_from('<II', body, 0)
            require(key in files and key not in seen, 'Missing/duplicate payload reference')
            seen.add(key)
            signed = files[key]
            payload = body[8:]
            require(len(payload) == signed['bytes'] and sha(payload) == signed['sha256'], 'Actual payload differs from signed directory')
            saved = manifest['files'][signed['path']]
            require(saved['sha256'] == signed['sha256'] and saved['mode'] == signed['mode'], 'Original manifest differs')
            for build in ['platform-build1', 'platform-build2']:
                staged = args.build_base / build / 'payload' / signed['path']
                require(staged.read_bytes() == payload and stat.S_IMODE(staged.stat().st_mode) == signed['mode'], 'Original package() staging differs')
            checks.append(dict(**signed, actual_payload_verified=True, both_original_stagings_match=True))
        require(kind in [0, 1, 2], 'Unexpected APK block type')
        end = offset + length
        offset = (end + 7) & ~7
        require(not any(raw[end:offset]), 'Nonzero block padding')
    require(offset == len(raw) and len(seen) == 19, 'Not all actual nineteen files were read')
    report = dict(schema=1, observations=observations, original_valid_copy='platform-packages2/samurai-platform-5-r2.apk',
                  valid_copy_sha256=expected_hash, valid_copy_bytes=12387,
                  all_nineteen_actual_payload_bytes_and_signed_modes_verified=True,
                  all_nineteen_match_both_original_package_function_stagings=True,
                  signed_dependency_pulseaudio_bluez_present=True, no_scripts_in_valid_copy=True,
                  files=checks, current_valid_original_copies=1, historical_two_builds_matched=True,
                  artifacts_not_rebuilt_or_overwritten=True, device_install_performed=False)
    (args.output / 'audit.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: report[k] for k in ['original_valid_copy', 'valid_copy_sha256', 'all_nineteen_actual_payload_bytes_and_signed_modes_verified', 'current_valid_original_copies', 'artifacts_not_rebuilt_or_overwritten']}))


if __name__ == '__main__':
    main()
