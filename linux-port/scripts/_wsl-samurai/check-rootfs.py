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

# Board default: never auto-suspend.  The upstream PowerDevil mobile
# defaults suspend after 900 s on AC and 300 s on battery/low battery.
# On this kernel s2idle drops USB/NCM and Wi-Fi, so an unattended suspend
# strands the device.  4-r19 ships /etc/xdg/powerdevilrc; a build that
# silently skips it leaves the upstream timers in force, which is why this
# is asserted here instead of trusting the image build log.
powerdevil = root / 'etc/xdg/powerdevilrc'
assert powerdevil.is_file(), 'Missing /etc/xdg/powerdevilrc (auto-suspend default)'
powerdevil_text = powerdevil.read_text()
# Both keys have to be 0.  KDE's desktop KCM writes AutoSuspendAction=0 for
# "Never", the Plasma Mobile KCM writes AutoSuspendIdleTimeoutSec=0; with
# only one of them the other UI shows a value that is not "Never".
for profile in ('AC', 'Battery', 'LowBattery'):
    section = '[' + profile + '][SuspendAndShutdown]'
    block_lines = []
    inside = False
    for line in powerdevil_text.splitlines():
        if line.strip() == section:
            inside = True
            continue
        if inside and line.lstrip().startswith('['):
            break
        if inside:
            block_lines.append(line.strip())
    assert 'AutoSuspendAction=0' in block_lines, \
        'AutoSuspendAction is not NoAction for ' + profile
    assert 'AutoSuspendIdleTimeoutSec=0' in block_lines, \
        'Auto-suspend not disabled for ' + profile
    for line in block_lines:
        if line.startswith('AutoSuspendAction='):
            assert line == 'AutoSuspendAction=0', \
                'Unexpected auto-suspend action: ' + line
_powerdevil_owner = ''
for _block in db.split('\n\n'):
    _pkg = ''
    _in_xdg = False
    for _line in _block.splitlines():
        if _line.startswith('P:'):
            _pkg = _line[2:]
        elif _line.startswith('F:etc/xdg'):
            _in_xdg = True
        elif _line.startswith('F:'):
            _in_xdg = False
        elif _in_xdg and _line == 'R:powerdevilrc':
            _powerdevil_owner = _pkg
assert _powerdevil_owner == 'samurai-desktop', \
    '/etc/xdg/powerdevilrc owner is ' + (_powerdevil_owner or 'none')
# A user-level file takes precedence over /etc/xdg.  It must not re-enable
# auto-suspend on a fresh image.
_user_rc = root / 'home' / a.user / '.config/powerdevilrc'
if _user_rc.is_file():
    _user_text = _user_rc.read_text()
    _user_actions = [line.strip() for line in _user_text.splitlines()
                     if line.strip().startswith('AutoSuspendAction=')]
    assert all(line == 'AutoSuspendAction=0' for line in _user_actions), \
        'user powerdevilrc sets a non-NoAction auto-suspend action'
    _user_timeouts = [line.strip() for line in _user_text.splitlines()
                      if line.strip().startswith('AutoSuspendIdleTimeoutSec=')]
    assert all(line == 'AutoSuspendIdleTimeoutSec=0' for line in _user_timeouts), \
        'user powerdevilrc sets a non-zero auto-suspend timeout'

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

# A board-private sshd drop-in is not an interface any distribution ships.
# 50-postmarketos-ui-policy.conf already provides UsePAM=yes, so nothing
# board-specific belongs under sshd_config.d, and an unowned file there is
# exactly the kind of stray that made the delivery image diverge from the
# official package set.
stray_sshd = root / 'etc/ssh/sshd_config.d/99-samurai.conf'
assert not stray_sshd.exists(), (
    'Unowned board-private sshd drop-in is still present: '
    + stray_sshd.relative_to(root).as_posix()
)

# Sensor chain. Two board facts have to hold, and both were verified on the
# handset (udev reports IIO_SENSOR_PROXY_TYPE="ssc-light ssc-compass ssc-accel
# ssc-proximity" plus ACCEL_MOUNT_MATRIX on fastrpc-sdsp):
#
#  1. the board rule exports the portrait matrix on both FastRPC nodes;
#  2. some rule that sorts before it adds "ssc-accel", because the board rule
#     is gated on that tag. iio-sensor-proxy's own 80- rule only adds
#     ssc-light/ssc-compass; postmarketos-base-ui 51-r0 adds the rest via
#     90-iio-sensor-proxy-proximity-sensor-enable.rules.
#
# If that earlier rule ever disappears the matrix stops being exported, and
# nothing else in the image would notice.
rules_dir = root / 'usr/lib/udev/rules.d'
board_sensors = rules_dir / '99-realme-rmx1931-sensors.rules'
assert board_sensors.is_file(), 'Missing board sensor rules: ' + board_sensors.name
_board_sensor_text = board_sensors.read_text()
assert _board_sensor_text.count('ENV{ACCEL_MOUNT_MATRIX}="-1,0,0;0,-1,0;0,0,1"') == 2, \
    'Board sensor rules must export the portrait matrix on both FastRPC nodes'

_ssc_accel_source = None
for _rule in sorted(rules_dir.glob('*.rules')):
    if _rule.name >= board_sensors.name:
        continue
    if 'ssc-accel' in _rule.read_text():
        _ssc_accel_source = _rule.name
        break
assert _ssc_accel_source is not None, (
    'No rule sorting before ' + board_sensors.name + ' exports '
    'IIO_SENSOR_PROXY_TYPE="ssc-accel", so ACCEL_MOUNT_MATRIX would never be '
    'set. postmarketos-base-ui 51-r0 ships '
    '90-iio-sensor-proxy-proximity-sensor-enable.rules for this.'
)

# The camera media graph only links sensor -> CSIPHY when the sensor's
# flash-leds reference can be matched by v4l2-async.  That needs the real
# v4l2_flash path inside leds-qcom-flash, which is compiled out entirely when
# CONFIG_V4L2_FLASH_LED_CLASS is off.  A stub .ko silently leaves all four
# sensors with links=0, so gate on the module present *and* actually linked.
_flash_modules = []
for _moddir in sorted((root / 'lib/modules').glob('*')):
    if not _moddir.is_dir():
        continue
    _qcom = _moddir / 'kernel/drivers/leds/flash/leds-qcom-flash.ko'
    _v4l2 = _moddir / 'kernel/drivers/media/v4l2-core/v4l2-flash-led-class.ko'
    _flash_modules.append({
        'release': _moddir.name,
        'leds_qcom_flash': _qcom.is_file(),
        'v4l2_flash_led_class': _v4l2.is_file(),
        'qcom_refs_v4l2_flash': (
            b'v4l2_flash_init' in _qcom.read_bytes() if _qcom.is_file() else False
        ),
    })
assert _flash_modules, 'no lib/modules/<release> in the image'

# Only the module tree that matches the kernel the board actually boots must be
# correct.  An image may carry several <release> trees (the repo baseline and
# the deployed build), and the stale one is not a shipping defect by itself.
_running = [m for m in _flash_modules if m['release'].endswith('-usbwake-otg')]
assert _running, (
    'no lib/modules tree matching the deployed kernel '
    '(expected a <release>-usbwake-otg directory); got '
    + ', '.join(m['release'] for m in _flash_modules)
)
for _m in _running:
    assert _m['leds_qcom_flash'], (
        _m['release'] + ': leds-qcom-flash.ko missing; the camera flash '
        'sub-device would never register, so all sensor links stay 0'
    )
    assert _m['v4l2_flash_led_class'], (
        _m['release'] + ': v4l2-flash-led-class.ko missing; '
        'CONFIG_V4L2_FLASH_LED_CLASS was not built, leds-qcom-flash then '
        'carries the stub qcom_flash_v4l2_init() and no flash sub-device is '
        'registered, which blocks camss_subdev_notifier_complete()'
    )
    assert _m['qcom_refs_v4l2_flash'], (
        _m['release'] + ': leds-qcom-flash.ko has no v4l2_flash_init reference, '
        'so it was built from the stub branch'
    )

report = {
    'installed_package_count': len(records),
    'custom_packages': {n: records[n]['V'] for n in required},
    'installed_files_verified': checks,
    'arm64_elfs_verified': elfs,
    'gi_qmi_namespace_loaded': True,
    'legacy_power_profile': legacy,
    'flash_v4l2_modules': _flash_modules,
    'kernel_maintenance_cleanliness': 'requires separate source review; not established by this check',
    'hardware_tested': False,
}
print(json.dumps(report, indent=2))
if a.require_maintenance_clean and legacy:
    raise SystemExit('Legacy power profile remains; this is a bring-up baseline')
