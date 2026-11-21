#!/usr/bin/env python3
"""Check a newly built offline root tree; never start its hardware services."""
from pathlib import Path
import argparse, base64, hashlib, json, re, shutil, struct, subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--root', type=Path, required=True)
p.add_argument('--packages', type=Path, required=True, help='This build packages/edge directory')
p.add_argument('--user', default='user')
p.add_argument('--require-maintenance-clean', action='store_true')
a = p.parse_args()
root = a.root.resolve()
packages = a.packages.resolve()
if root == Path('/') or not (root / 'etc/alpine-release').is_file():
    p.error('Offline Alpine root required')
db = (root / 'lib/apk/db/installed').read_text()
records = {}
selected = set()
required = [
    'device-realme-samurai', 'device-realme-samurai-kernel-none',
    'samurai-camera-config', 'samurai-camera-stack', 'libcamera', 'libcamera-ipa',
    'libcamera-tools', 'libcamera-gstreamer', 'libcamera-v4l2',
    'modemmanager', 'libmm-glib', 'geoclue',
    'pipewire', 'pipewire-libs', 'pipewire-spa-libcamera', 'gst-plugin-pipewire',
    'samurai-libssc', 'samurai-hexagonrpcd', 'samurai-radio-tools',
    'samurai-platform', 'samurai-gnss-assist', 'samurai-ssc',
    'samurai-desktop', 'usb-signaller', 'unudhcpd', 'samurai-systemd',
]
for block in db.split('\n\n'):
    row = {}
    for line in block.splitlines():
        k, sep, v = line.partition(':')
        if k in ['P', 'V', 'A', 'o', 'c']:
            row[k] = v
    if 'P' in row:
        records[row['P']] = row
# Packages that are built locally must also have a matching APK in the
# build output.  Upstream packages (modemmanager, geoclue, pipewire, ...)
# come from the binary repositories and have no local artifact.
local = {'device-realme-samurai', 'device-realme-samurai-kernel-none',
         'samurai-camera-config', 'samurai-camera-stack', 'libcamera',
         'libcamera-ipa', 'libcamera-tools', 'libcamera-gstreamer', 'libcamera-v4l2',
         'samurai-libssc', 'samurai-hexagonrpcd', 'samurai-radio-tools',
         'samurai-platform', 'samurai-gnss-assist', 'samurai-ssc',
         'samurai-desktop', 'samurai-systemd', 'usb-signaller', 'unudhcpd'}
for name in required:
    assert name in records, 'Missing package: ' + name
    row = records[name]
    if name in local:
        apk = name + '-' + row['V'] + '.apk'
        assert any((directory / apk).is_file()
                   for directory in [packages, packages / 'aarch64', packages / 'noarch']), apk
    selected.add(name)
checks = 0
elfs = 0
for block in db.split('\n\n'):
    current = ''
    directory = ''
    path = None
    for line in block.splitlines():
        k, sep, value = line.partition(':')
        if k == 'P':
            current = value
        elif k == 'F':
            directory = value
        elif k == 'R':
            path = directory + '/' + value
        elif k == 'Z' and current in selected and path:
            f = root / path
            assert f.exists() or f.is_symlink(), 'Missing installed file: ' + path
            if not f.is_file() or f.is_symlink():
                continue
            if value.startswith(('Q1', 'Q2')):
                data = f.read_bytes()
                algorithm = 'sha1' if value[:2] == 'Q1' else 'sha256'
                assert hashlib.new(algorithm, data).digest() == base64.b64decode(value[2:]), 'Package file changed: ' + path
                checks += 1
                if data.startswith(bytes([127]) + b'ELF'):
                    assert data[4:6] == bytes([2, 1]) and struct.unpack('<H', data[18:20])[0] == 183, 'Non-ARM64 ELF: ' + path
                    elfs += 1
assert checks > 50, 'Unrecognized installed-file checksum format'

# postmarketos-ui-plasma-mobile lists these in _pmb_recommends. pmbootstrap
# installs them unless --no-recommends is given; skipping them produces a
# bootable image with a nearly empty app grid (20261118 did exactly that).
_plasma_mobile_recommends = [
    'dolphin', 'konsole', 'kate', 'kclock', 'kweather', 'krecorder',
    'plasma-camera', 'plasma-dialer', 'plasma-phonebook',
    'qmlkonsole', 'spacebar', 'firefox-esr', 'mobile-config-firefox',
    'discover',
]
# postmarketos-ui-plasma-mobile-extras carries its own _pmb_recommends;
# pmbootstrap recurses into it, so ui_extras=true should bring these too.
_plasma_mobile_extras_recommends = [
    'alligator', 'audiotube', 'elisa', 'itinerary', 'kalgebra', 'kalk',
    'kasts', 'kdeconnect', 'keysmith',
]
for name in _plasma_mobile_recommends + _plasma_mobile_extras_recommends:
    assert name in records, 'Missing UI recommend: ' + name
# A locally built package must not be pinned to one APK file hash in world:
# "<name><Q1...=" makes the next apk upgrade unsolvable. Same for a version
# pin that the offline build recorded instead of the intended package name.
world = (root / 'etc/apk/world').read_text().splitlines()
assert world and not any('<Q' in line for line in world), \
    'world contains APK checksum pins'
logind_conf = root / 'etc/elogind/logind.conf'
logind_paths = [root / 'etc/systemd/logind.conf',
                root / 'usr/lib/systemd/logind.conf']
assert any(f.is_file() and 'HandlePowerKey=ignore' in f.read_text()
          for f in logind_paths), 'Missing HandlePowerKey=ignore'

# This image is kernel=none and boots the F2FS rootfs directly, so there is no
# installed kernel release to build an initramfs from. The packaged mkinitfs
# trigger must therefore bypass itself; otherwise it exits 1 and apk records
# postmarketos-mkinitfs as broken_script, which appends "1 error" to every
# later transaction. The stale flag must not exist either.
def trigger_text():
    import tarfile
    with tarfile.open(root / 'lib/apk/db/scripts.tar.gz') as archive:
        for name in archive.getnames():
            if name.startswith('postmarketos-mkinitfs-') and name.endswith('.trigger'):
                return archive.extractfile(name).read().decode()
    return ''


assert 'KERNEL_INSTALL_BYPASS=1' in trigger_text(), \
    'mkinitfs trigger does not bypass itself for kernel=none'
_installed = (root / 'lib/apk/db/installed').read_text()
for _block in _installed.split('\n\n'):
    if _block.startswith('P:postmarketos-mkinitfs\n') or '\nP:postmarketos-mkinitfs\n' in _block:
        assert '\nf:s\n' not in _block, 'stale broken_script flag on postmarketos-mkinitfs'

systemd = (root / 'usr/lib/systemd/system').is_dir()
if systemd:
    for service in [
        'samurai-radio.service', 'samurai-ssc.service', 'samurai-gnss-assist.service',
        'samurai-usb-network.service', 'samurai-usb-recover.service',
        'usb-signaller.service', 'unudhcpd@.service', 'sshd.service',
        'NetworkManager.service', 'ModemManager.service', 'bluetooth.service',
        'iio-sensor-proxy.service', 'plasma-mobile.service',
    ]:
        assert (root / 'usr/lib/systemd/system' / service).is_file(), service
    wants = root / 'etc/systemd/system/multi-user.target.wants'
    for unit in [
        'samurai-radio.service', 'samurai-ssc.service', 'samurai-gnss-assist.service',
        'samurai-usb-network.service', 'samurai-usb-recover.service',
        'usb-signaller.service', 'usb-signaller-developer-mode.service',
        'unudhcpd@usb0.service', 'NetworkManager.service', 'ModemManager.service',
        'iio-sensor-proxy.service',
    ]:
        assert (wants / unit).is_symlink(), 'Not enabled: ' + unit
    assert (root / 'etc/systemd/system/display-manager.service').is_symlink(), \
        'display-manager.service missing'
    for preset in ['50-samurai.preset', '90-base.preset']:
        assert (root / 'usr/lib/systemd/system-preset' / preset).is_file(), preset

    # systemd-analyze --root= catches broken ExecStart paths, unresolvable
    # dependencies and malformed units that a plain existence check misses.
    # A minimal container warns about man pages and legacy /var/run paths;
    # those are not unit errors. Skip cleanly when the host lacks the tool.
    analyze = shutil.which('systemd-analyze')
    if analyze:
        for unit in [
            'samurai-radio.service', 'samurai-ssc.service',
            'samurai-gnss-assist.service', 'samurai-usb-network.service',
            'samurai-usb-recover.service', 'usb-signaller.service',
            'unudhcpd@usb0.service', 'sshd.service', 'ModemManager.service',
            'iio-sensor-proxy.service', 'plasma-mobile.service',
        ]:
            result = subprocess.run(
                [analyze, '--root=' + str(root), 'verify', unit],
                capture_output=True, text=True)
            problems = [
                line for line in result.stderr.splitlines()
                if line.strip()
                and 'legacy directory /var/run/' not in line
                and 'man ' not in line
            ]
            assert not problems, unit + ': ' + '; '.join(problems[:3])
else:
    for service in [
        'samurai-radio', 'usb-signaller', 'samurai-usb-network', 'unudhcpd.usb0',
        'sshd', 'bluetooth', 'elogind', 'iio-sensor-proxy', 'tinydm',
        'samurai-ssc', 'samurai-gnss-assist', 'networkmanager',
    ]:
        init_file = root / 'etc/init.d' / service
        assert init_file.is_file() or init_file.is_symlink(), service
        assert any((root / 'etc/runlevels' / level / service).is_symlink()
                   for level in ['boot', 'default']), service
for command in [
    'usr/lib/bluetooth/bluetoothd',
    'usr/libexec/iio-sensor-proxy', 'usr/sbin/sshd.pam',
    'usr/libexec/samurai-hexagonrpcd', 'usr/bin/usb-signaller',
    'usr/sbin/samurai-tqftpserv', 'usr/sbin/samurai-rmtfs-cow',
]:
    assert (root / command).is_file(), 'Missing service executable: ' + command
for name in ['ssc-library', 'ssc-daemon']:
    for line in (root / f'usr/share/samurai/{name}.sha256').read_text().splitlines():
        digest, path = line.split('  ', 1)
        assert hashlib.sha256((root / path.lstrip('/')).read_bytes()).hexdigest() == digest, name
result = subprocess.run(
    ['chroot', str(root), '/usr/bin/python3', '-c',
     "import gi; gi.require_version('Qmi','1.0'); from gi.repository import GLib,Qmi; print('GI-QMI-load-ok')"],
    capture_output=True, text=True,
)
assert result.returncode == 0, result.stderr
legacy = []
for f in (root / 'etc/modprobe.d').glob('*.conf'):
    if 'experimental_p_imx319_power' in f.read_text():
        legacy.append(f.relative_to(root).as_posix())
report = {
    'installed_package_count': len(records),
    'custom_packages': {n: records[n]['V'] for n in required},
    'installed_files_verified': checks,
    'arm64_elfs_verified': elfs,
    'gi_qmi_namespace_loaded': True,
    'legacy_power_profile': legacy,
    'kernel_maintenance_cleanliness': 'requires separate source review; not established by this check',
    'hardware_tested': False,
}
print(json.dumps(report, indent=2))
if a.require_maintenance_clean and legacy:
    raise SystemExit('Legacy power profile remains; this is a bring-up baseline')
