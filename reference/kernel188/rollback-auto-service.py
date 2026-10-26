"""Quiesce the failed PM instance before restoring original rootfs service files."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

os.umask(0o077)
out = Path('/var/lib/samurai/k188-rollback')
assert not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k188-reboot-runtime/boot-id-private.txt').read_bytes()
assert Path('/var/lib/samurai/k188-pm-failure/summary.json').exists()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'crashed'
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
(out / 'dmesg-before-private.txt').write_bytes(subprocess.check_output(['dmesg']))
for name in ['iio-sensor-proxy', 'samurai-ssc']:
    p = subprocess.run(['rc-service', name, 'stop'], capture_output=True, timeout=45)
    (out / (name + '-stop-private.txt')).write_bytes(p.stdout + p.stderr)
    assert p.returncode == 0, name
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip() == 'offline'
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
assert Path('/sys/class/remoteproc/remoteproc0/firmware').read_text().strip() == 'qcom/sm8150/realme/samurai/slpi.mdt'
assert not subprocess.run(['pidof', 'samurai-hexagonrpcd', 'iio-sensor-proxy'], capture_output=True).stdout.strip()
files = json.loads(Path('/var/lib/samurai/k188-deploy/original-files-private.json').read_text())
# Archive the exact attempted deployment and generated RAM tree before removing its entrypoints.
subprocess.run(['tar', '-czf', str(out / 'failed-deployment-private.tar.gz'), '/run/samurai-ssc',
    *[record['path'] for record in files if Path(record['path']).exists()]],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
p = subprocess.run(['rc-update', 'del', 'samurai-ssc', 'default'], capture_output=True)
(out / 'rc-update-private.txt').write_bytes(p.stdout + p.stderr)
assert p.returncode == 0
for record in files:
    dest = Path(record['path'])
    assert not dest.is_symlink()
    if record['existed']:
        backup = Path(record['backup'])
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == record['sha256']
        tmp = dest.with_name(dest.name + '.k188-restore')
        assert not tmp.exists()
        shutil.copyfile(backup, tmp)
        tmp.chmod(record['mode'])
        tmp.replace(dest)
        assert hashlib.sha256(dest.read_bytes()).hexdigest() == record['sha256']
    elif dest.exists():
        dest.unlink()
assert not Path('/etc/runlevels/default/samurai-ssc').is_symlink()
assert Path('/etc/init.d/iio-sensor-proxy').read_bytes() == Path('/var/lib/samurai/k188-deploy/original-2-private').read_bytes()
subprocess.run(['sha256sum','-c','/var/lib/samurai/k188-deploy/source-manifest-private.sha256'],check=True,stdout=subprocess.DEVNULL)
subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=subprocess.DEVNULL)
(out / 'dmesg-after-private.txt').write_bytes(subprocess.check_output(['dmesg']))
summary = dict(stage=188, auto_service_rolled_back=True, original_iio_service_restored=True,
    original_rootfs_files_restored=True, slpi_offline=True, sensor_supplies_off=True,
    original_firmware_pointer_restored=True, temporary_daemon_and_proxy_stopped=True,
    source_archive_and_nv_preserved=True, taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    awake_client_tests_passed=True, suspend_trial_passed=False, reboot_or_flash_performed=False)
(out / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
