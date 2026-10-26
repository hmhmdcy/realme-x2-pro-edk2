from pathlib import Path
import dbus, hashlib, json, os, shutil, subprocess
os.umask(0o077)
root = Path('/var/lib/samurai'); stage = root / 'k207-mcfg-stage'; out = root / 'k207-mcfg-deploy-r2'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207-runtime/boot-id-private.txt').read_bytes()
for name, digest in json.loads((stage / 'artifacts-r2-private.json').read_text()).items():
    assert hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest
program = Path('/usr/sbin/samurai-modem-configs'); helper = Path('/usr/sbin/samurai-wifi')
assert not program.exists()
assert hashlib.sha256(helper.read_bytes()).hexdigest() == 'ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd'
firmware = Path('/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai')
assert not (firmware / 'modem_pr/mcfg').exists()
state_dir=Path('/run/samurai-wifi/mcfg-state'); state_dir.mkdir(mode=0o700)
manifest = state_dir/'source-manifest-private.json'; assert not manifest.exists()
bus = dbus.SystemBus(private=True)
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1/Modem/0'), 'org.freedesktop.DBus.Properties')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0
owner = str(bus.get_name_owner('org.freedesktop.ModemManager1'))
pid = int(Path('/run/samurai-wifi/tftp.pid').read_text())
started = Path('/proc/%d/stat' % pid).read_text().split(') ', 1)[1].split()[19]
out.mkdir(mode=0o700); (out / 'boot-id-private.txt').write_bytes(boot)
shutil.copyfile(helper, out / 'samurai-wifi-before-mcfg.sh')
devices = [('/dev/' + p.name) for p in Path('/sys/class/block').iterdir() if (p / 'uevent').exists() and 'PARTNAME=modem' in (p / 'uevent').read_text().splitlines()]
assert len(devices) == 1
device = devices[0]
assert subprocess.check_output(['lsblk', '-ndo', 'PARTLABEL', device], text=True).strip() == 'modem'
assert int(subprocess.check_output(['blockdev', '--getsize64', device], text=True)) == 524288 * 512
mountpoint = out / 'stock'; mountpoint.mkdir(mode=0o700)
def command(args, label, timeout=45):
    p = subprocess.run(args, capture_output=True, timeout=timeout)
    (out / (label + '-private.log')).write_bytes(p.stdout + p.stderr); assert p.returncode == 0, label
    return p
mounted = False
try:
    command(['mount', '-t', 'vfat', '-o', 'ro,nosuid,nodev,noexec', device, str(mountpoint)], 'mount-stock')
    mounted = True
    copied = json.loads(command(['python3', str(stage / 'samurai-modem-configs-new.py'), str(mountpoint / 'image'), str(firmware), str(manifest)], 'publish-stock-mcfg').stdout)
    assert copied['regular_files'] == 173 and copied['total_bytes'] == 8807671 and copied['mdtime_bytes'] == 12
    current = json.loads(manifest.read_text())
    prior = json.loads((root / 'k207-stock-mcfg-inventory/mcfg-source-manifest-private.json').read_text())
    assert current == prior
    shutil.copyfile(manifest, out / 'stock-to-ram-manifest-private.json')
finally:
    if mounted: command(['umount', str(mountpoint)], 'unmount-stock')
for source, target in [(stage / 'samurai-modem-configs-new.py', program), (stage / 'samurai-wifi-new-r2.sh', helper)]:
    temp = target.with_name(target.name + '.k207-mcfg-new'); temp.write_bytes(source.read_bytes()); temp.chmod(0o755); os.replace(temp, target)
read = command([str(stage / 'native-readonly-client'), '0', 'read-mdtime'], 'native-read-mdtime')
read_result = json.loads(read.stdout)
assert read_result['qrtr_transactions'] == 1 and read_result['readback_bytes_compared'] == 12
assert Path('/proc/%d/stat' % pid).read_text().split(') ', 1)[1].split()[19] == started
assert str(bus.get_name_owner('org.freedesktop.ModemManager1')) == owner
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location', 'Enabled')) == 0; bus.close()
command(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], 'nv-source-check')
assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
result = dict(stage=207, same_verified_first207_boot=True, same_handset_stock_mcfg_staged_to_ram=copied, inventory_and_all_ram_hashes_match=True, native_readonly_transfer=read_result, tftp_same_process=True, modem_owner_unchanged=True, modem_restarted=False, gps_started=False, stock_source_readonly_and_unmounted=True, nv_sources_unchanged=True, startup_helper_installed=True, wifi_helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(), mcfg_helper_sha256=hashlib.sha256(program.read_bytes()).hexdigest(), taint=int(Path('/proc/sys/kernel/tainted').read_text()), no_explicit_pdc_load_select_activate=True, no_partition_writes=True, boot_automatic_copy_not_yet_verified=True)
(out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))
