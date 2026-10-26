#!/usr/bin/python3
"""Stage this handset's stock MCFG subtree from a read-only FAT into RAM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile


def filesystem(path):
    record = json.loads(subprocess.check_output(['findmnt', '-J', '-T', str(path), '-o', 'FSTYPE,OPTIONS']))
    return record['filesystems'][0]


def stage(source_image, firmware_root, manifest_path):
    source_image = Path(source_image)
    firmware_root = Path(firmware_root)
    manifest_path = Path(manifest_path)
    fs = filesystem(source_image)
    if fs['fstype'] != 'vfat' or 'ro' not in fs['options'].split(','):
        raise ValueError('Stock modem source must be a read-only FAT mount')
    for path in [firmware_root, manifest_path.parent]:
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('RAM staging directories must be private and owned by this process')
        if filesystem(path)['fstype'] != 'tmpfs':
            raise ValueError('Firmware and manifest staging must stay in tmpfs')
    if manifest_path.exists() or manifest_path.is_symlink():
        raise FileExistsError('MCFG staging manifest already exists')
    source = source_image / 'modem_pr/mcfg'
    if not source.is_dir() or source.is_symlink():
        raise ValueError('Stock MCFG directory missing')
    paths = sorted(source.rglob('*'))
    files = []
    total = 0
    for path in paths:
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Only regular stock MCFG files are supported')
        files.append(path)
        total += info.st_size
        if len(files) > 4096 or total > 64 * 1024 * 1024:
            raise ValueError('Stock MCFG staging exceeds RAM budget')
    if not (source / 'configs/mcfg_sw/mdtime.txt').is_file():
        raise ValueError('Stock MCFG time manifest missing')
    parent = firmware_root / 'modem_pr'
    parent.mkdir(mode=0o700, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError('Invalid firmware subtree parent')
    destination = parent / 'mcfg'
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('MCFG firmware subtree already exists')
    temporary = Path(tempfile.mkdtemp(prefix='.mcfg-stage-', dir=parent))
    manifest = {}
    for path in files:
        relative = path.relative_to(source)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        target = temporary / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o600)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise IOError('MCFG RAM copy verification failed')
        manifest[str(Path('modem_pr/mcfg') / relative)] = dict(bytes=len(data), sha256=digest)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('MCFG destination changed during staging')
    temporary.rename(destination)
    with manifest_path.open('x') as output:
        json.dump(manifest, output, indent=2)
        output.write('\n')
    return dict(stock_source_read_only=True, ram_subtree_published=True, regular_files=len(manifest), total_bytes=total, all_ram_file_hashes_verified=True, mdtime_bytes=(destination / 'configs/mcfg_sw/mdtime.txt').stat().st_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_image', type=Path)
    parser.add_argument('firmware_root', type=Path)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    print(json.dumps(stage(args.source_image, args.firmware_root, args.manifest)))


if __name__ == '__main__':
    main()
