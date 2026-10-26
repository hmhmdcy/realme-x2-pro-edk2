"""Install the reviewed service with originals backed up; never start SLPI here."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k188-deploy')
require = lambda condition: condition or (_ for _ in ()).throw(RuntimeError('Deployment precondition failed'))
require(not out.exists())
require(os.uname().version.startswith('#183 '))
require(Path('/proc/sys/kernel/tainted').read_text().strip() == '0')
require(Path('/sys/class/remoteproc/remoteproc0/name').read_text().strip() == 'slpi')
require(Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline')
require(Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0')
require(not subprocess.run(['pidof', 'iio-sensor-proxy', 'hexagonrpcd-v5', 'samurai-hexagonrpcd'], capture_output=True).stdout.strip())
require('need dbus\n' in Path('/etc/init.d/iio-sensor-proxy').read_text())
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
upload = Path('/var/lib/samurai/k188-tools')
source = Path('/var/lib/samurai/k111-sensor-sources-readonly')
daemon = Path('/var/lib/samurai/k113-tools/hexagonrpcd-v5')
library = Path('/var/lib/samurai/k184-libssc-r2/build-r4/src/libssc.so.2')
require(hashlib.sha256(daemon.read_bytes()).hexdigest() == '1902f1b62aea2d0038a9138ae1cd996941f0d0deaa3804d9317ebdc69836e270')
require(hashlib.sha256(library.read_bytes()).hexdigest() == '45570ea41d07fd4300069b5e3ed254f5dfc0c9b660a269d293943a9834566006')
database = Path('/lib/apk/db/installed').read_bytes()
system_library = Path('/usr/lib/libssc.so.2').read_bytes()
(out / 'dmesg-before-private.txt').write_bytes(subprocess.check_output(['dmesg']))

def manifest(files, path):
    require(all(p.is_file() and not p.is_symlink() for p in files))
    path.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p) + '\n' for p in files))
    subprocess.run(['sha256sum', '-c', str(path)], check=True, stdout=subprocess.DEVNULL)

files = []
for name in ['sdsp', 'sensors-vendor/config', 'sensors-persist/registry']:
    require(not any(p.is_symlink() for p in (source / name).rglob('*')))
    files.extend(sorted(p for p in (source / name).rglob('*') if p.is_file()))
files.extend([source / 'sensors-vendor/sns_reg_config',
    Path('/var/lib/samurai/k113-tools/magnetometer-config-escaped-control-private.json'),
    Path('/var/lib/samurai/k112-project-metadata/modemType')])
manifest(files, out / 'source-manifest-private.sha256')
firmware = Path('/lib/firmware/qcom/sm8150/realme/samurai-a11-r187')
firmware_files = sorted(p for p in firmware.iterdir() if p.name != 'SHA256SUMS')
require(len(firmware_files) == 24)
subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=firmware, check=True, stdout=subprocess.DEVNULL)
manifest(firmware_files, out / 'firmware-manifest-private.sha256')
config = dict(source=str(source), manifest=str(out / 'source-manifest-private.sha256'),
    firmware_manifest=str(out / 'firmware-manifest-private.sha256'),
    mag_config='/var/lib/samurai/k113-tools/magnetometer-config-escaped-control-private.json',
    modem_type='/var/lib/samurai/k112-project-metadata/modemType',
    skip_boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
(out / 'config-private.json').write_text(json.dumps(config, indent=2) + '\n')
changes = [
    (upload / 'samurai-ssc.py', Path('/usr/sbin/samurai-ssc'), 0o755),
    (upload / 'samurai-ssc.initd', Path('/etc/init.d/samurai-ssc'), 0o755),
    (upload / 'iio-sensor-proxy.initd', Path('/etc/init.d/iio-sensor-proxy'), 0o755),
    (upload / 'iio-sensor-proxy.conf', Path('/etc/conf.d/iio-sensor-proxy'), 0o644),
    (daemon, Path('/usr/libexec/samurai-hexagonrpcd'), 0o755),
    (library, Path('/usr/lib/samurai/ssc/libssc.so.2'), 0o755),
    (out / 'config-private.json', Path('/etc/samurai-ssc.json'), 0o600),
]
backups = []
for index, (_, dest, mode) in enumerate(changes):
    require(not dest.is_symlink())
    record = dict(path=str(dest), existed=dest.exists())
    if dest.exists():
        backup = out / ('original-' + str(index) + '-private')
        shutil.copy2(dest, backup)
        record.update(backup=str(backup), mode=dest.stat().st_mode & 0o777,
                      sha256=hashlib.sha256(backup.read_bytes()).hexdigest())
    backups.append(record)
(out / 'original-files-private.json').write_text(json.dumps(backups, indent=2) + '\n')
link = Path('/etc/runlevels/default/samurai-ssc')
require(not link.exists() and not link.is_symlink())
(out / 'installation-started.txt').write_text('1\n')
try:
    for src, dest, mode in changes:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + '.k188-new')
        require(not tmp.exists())
        shutil.copyfile(src, tmp)
        tmp.chmod(mode)
        tmp.replace(dest)
    subprocess.run(['sh', '-n', '/etc/init.d/samurai-ssc'], check=True)
    subprocess.run(['sh', '-n', '/etc/init.d/iio-sensor-proxy'], check=True)
    subprocess.run(['rc-update', 'add', 'samurai-ssc', 'default'], check=True, stdout=subprocess.DEVNULL)
    require(link.is_symlink())
    require(Path('/lib/apk/db/installed').read_bytes() == database)
    require(Path('/usr/lib/libssc.so.2').read_bytes() == system_library)
    p = subprocess.run(['/usr/sbin/samurai-ssc', 'start'], capture_output=True, timeout=10)
    (out / 'same-boot-refusal-private.txt').write_bytes(p.stdout + p.stderr)
    require(p.returncode == 1 and b'reboot required' in p.stderr)
    require(Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline')
    require(Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0')
except Exception:
    if link.is_symlink():
        link.unlink()
    for record in backups:
        dest = Path(record['path'])
        if record['existed']:
            shutil.copy2(record['backup'], dest)
            dest.chmod(record['mode'])
        elif dest.exists():
            dest.unlink()
    (out / 'installation-rolled-back.txt').write_text('1\n')
    raise
summary = dict(stage=188, persistent_files_installed=True, service_enabled_for_next_boot=True,
    same_used_boot_start_refused=True, slpi_not_started=True, original_files_backed_up=True,
    private_source_files=len(files), same_handset_firmware_files=len(firmware_files),
    default_system_library_unchanged=True, package_database_unchanged=True,
    native_boot_verified=False)
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
(out / 'installation-completed.txt').write_text('1\n')
print(json.dumps(summary))
