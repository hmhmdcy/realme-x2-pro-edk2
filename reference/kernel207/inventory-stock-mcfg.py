"""Inventory this handset's modem FAT read-only; no config load or activation."""
from pathlib import Path
import hashlib, json, os, subprocess
os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207-runtime/boot-id-private.txt').read_bytes()
out = root / 'k207-stock-mcfg-inventory'; out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
devices = []
for item in Path('/sys/class/block').iterdir():
    p = item / 'uevent'
    if p.exists() and 'PARTNAME=modem' in p.read_text().splitlines(): devices.append('/dev/' + item.name)
assert len(devices) == 1
device = devices[0]
assert subprocess.check_output(['lsblk', '-ndo', 'PARTLABEL', device], text=True).strip() == 'modem'
assert int(subprocess.check_output(['blockdev', '--getsize64', device], text=True)) == 524288 * 512
mountpoint = out / 'stock'; mountpoint.mkdir(mode=0o700)
mounted = False
try:
    p = subprocess.run(['mount', '-t', 'vfat', '-o', 'ro,nosuid,nodev,noexec', device, str(mountpoint)], capture_output=True)
    (out / 'mount-private.log').write_bytes(p.stdout + p.stderr); assert p.returncode == 0
    mounted = True
    assert 'ro' in json.loads(subprocess.check_output(['findmnt', '-J', '-T', str(mountpoint), '-o', 'OPTIONS']))['filesystems'][0]['options'].split(',')
    tree = mountpoint / 'image/modem_pr/mcfg'
    paths = sorted(p for p in tree.rglob('*') if p.is_file()) if tree.exists() else []
    assert not any(p.is_symlink() for p in tree.rglob('*')) if tree.exists() else True
    manifest = {str(p.relative_to(mountpoint / 'image')): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths}
    (out / 'mcfg-source-manifest-private.json').write_text(json.dumps(manifest, indent=2) + '\n')
    mdtime = tree / 'configs/mcfg_sw/mdtime.txt'
    if mdtime.is_file(): (out / 'mdtime-source-private.txt').write_bytes(mdtime.read_bytes())
    report = dict(stage=207, current_new_boot_verified=True, same_handset_modem_partition_read_only=True, stock_mcfg_directory_present=tree.is_dir(), stock_mcfg_regular_files=len(paths), stock_mcfg_total_bytes=sum(v['bytes'] for v in manifest.values()), requested_mdtime_present_in_stock=mdtime.is_file(), requested_mdtime_bytes=mdtime.stat().st_size if mdtime.is_file() else None, read_only_only=True, no_configuration_load_select_activate=True, no_partition_writes=True)
finally:
    if mounted:
        p = subprocess.run(['umount', str(mountpoint)], capture_output=True)
        (out / 'unmount-private.log').write_bytes(p.stdout + p.stderr); assert p.returncode == 0
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n'); print(json.dumps(report))
