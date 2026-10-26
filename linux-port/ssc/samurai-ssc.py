#!/usr/bin/python3
"""Own the Samurai SLPI/file-service lifetime and a per-boot private RAM registry."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time

CONTROL = Path('/run/samurai-ssc')
CONFIG = Path('/etc/samurai-ssc.json')
POWER = Path('/sys/devices/platform/sensor-power/state')
BOOT = Path('/proc/sys/kernel/random/boot_id')
DAEMON = Path('/usr/libexec/samurai-hexagonrpcd')
LIBRARY = Path('/usr/lib/samurai/ssc/libssc.so.2')
FW = 'qcom/sm8150/realme/samurai-a11-r187/slpi.mdt'
DAEMON_HASH = '1902f1b62aea2d0038a9138ae1cd996941f0d0deaa3804d9317ebdc69836e270'
LIBRARY_HASH = '45570ea41d07fd4300069b5e3ed254f5dfc0c9b660a269d293943a9834566006'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def text(path):
    return Path(path).read_text().strip()


def save(record):
    tmp = CONTROL / 'state.json.tmp'
    tmp.write_text(json.dumps(record, indent=2) + '\n')
    tmp.replace(CONTROL / 'state.json')


def process_identity(pid):
    """Include start ticks so a recycled PID can never receive our stop signal."""
    try:
        proc = Path('/proc') / str(pid)
        tail = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'start_ticks': int(tail[19]),
                'exe': str((proc / 'exe').resolve(strict=True)),
                'cmdline': (proc / 'cmdline').read_bytes().split(b'\0')[:-1]}
    except (OSError, ValueError, IndexError):
        return None


def owned_process(record):
    identity = process_identity(record.get('pid', -1))
    return bool(identity and identity['start_ticks'] == record.get('start_ticks')
                and identity['exe'] == str(DAEMON)
                and identity['cmdline'] == [os.fsencode(DAEMON), b'-f', b'/dev/fastrpc-sdsp',
                    b'-d', b'sdsp', b'-R', os.fsencode(CONTROL / 'root'), b'-s'])


def check_hash(path, expected):
    require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected,
            'Pinned SSC file does not match: ' + str(path))


def run(args, log, timeout=30, env=None):
    with (CONTROL / log).open('ab') as stream:
        result = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, env=env)
    require(result.returncode == 0, 'SSC command failed; private log: ' + log)


def write_node(path, value):
    # sysfs writes may block; a child gives every transition a bounded wait.
    run(['/bin/sh', '-c', 'printf "%s\\n" "$2" > "$1"', 'sh', str(path), value],
        'transitions-private.log', timeout=16)


def stop(record, node):
    if not record:
        require(text(node / 'state') == 'offline' and text(POWER) == 'vdd=0 vddio=0',
                'Refusing to stop an SLPI instance owned by another service')
        return
    require(record['boot_id'] == text(BOOT), 'State belongs to a different boot')
    if text(node / 'state') != 'offline':
        # Keep the file server alive until the DSP/GLINK teardown has completed.
        write_node(node / 'state', 'stop')
    require(text(node / 'state') == 'offline', 'DSP not offline; retaining daemon and power')
    if owned_process(record):
        os.kill(record['pid'], signal.SIGTERM)
        deadline = time.monotonic() + 10
        while owned_process(record) and time.monotonic() < deadline:
            time.sleep(.1)
        require(not owned_process(record), 'File service did not exit; preserving state')
    # A missing or recycled PID is never signalled.
    if text(POWER) != 'vdd=0 vddio=0':
        write_node(POWER, '0')
    write_node(node / 'firmware', record['original_firmware'])
    write_node(node / 'recovery', record['original_recovery'])
    record.update(started=False, stopped=True)
    save(record)


def prepare_root(config):
    root = CONTROL / 'root'
    require(not root.exists(), 'RAM tree already exists; refusing a second start')
    source = Path(config['source'])
    require(source.is_absolute() and source.is_dir(), 'Missing handset source archive')
    run(['sha256sum', '-c', config['manifest']], 'source-check-private.log')
    for name in ['sdsp', 'sensors-vendor/config', 'sensors-persist/registry']:
        require(not any(p.is_symlink() for p in (source / name).rglob('*')),
                'Unexpected source symlink')
    shutil.copytree(source / 'sdsp', root / 'dsp/sdsp')
    shutil.copytree(source / 'sensors-vendor/config', root / 'sensors/config')
    shutil.copytree(source / 'sensors-persist/registry', root / 'sensors/registry')
    for path in [root / 'sensors/registry', *(root / 'sensors/registry').rglob('*')]:
        os.chown(path, 0, 0)
    (root / 'sensors/registry').chmod(0o700)
    original = root / 'sensors/config/msmnile_mmc5603nj.json'
    check_hash(original, 'f84bee57583cdc8b8eec7c8cc0d2aea477ac20932ac1cde4e2b5b670fb091fe4')
    check_hash(config['mag_config'], '9fe3391f86ef0b70b3a6b696d4d353a594bc27b5765434c7d9ede489ac6a0535')
    shutil.copyfile(config['mag_config'], original)
    shutil.copyfile(source / 'sensors-vendor/sns_reg_config', root / 'sensors/sns_reg.conf')
    (root / 'oppoVersion').mkdir()
    require(text(config['modem_type']) == '4', 'Unexpected handset modem type')
    shutil.copyfile(config['modem_type'], root / 'oppoVersion/modemType')
    soc = root / 'socinfo'
    soc.mkdir()
    for name in ['soc_id', 'revision', 'family', 'machine']:
        shutil.copyfile(Path('/sys/devices/soc0') / name, soc / name)
    (soc / 'hw_platform').write_text('MTP\n')
    (soc / 'platform_subtype').write_text('Unknown\n')
    debug = Path('/sys/kernel/debug/qcom_socinfo')
    for name, dest in [('hardware_platform_subtype', 'platform_subtype_id'),
                       ('platform_version', 'platform_version')]:
        shutil.copyfile(debug / name, soc / dest)


def start(config, record, node):
    if record and record.get('started'):
        require(record['boot_id'] == text(BOOT) and owned_process(record)
                and text(node / 'state') == 'running', 'Existing SSC service is unhealthy')
        return
    require(not record, 'SLPI already attempted this boot; shared-pool restart remains unresolved')
    require(config.get('skip_boot_id') != text(BOOT), 'Install boot already used SLPI; reboot required')
    require(text(node / 'state') == 'offline' and text(POWER) == 'vdd=0 vddio=0',
            'SLPI is not idle')
    require(not subprocess.run(['pidof', 'hexagonrpcd', 'hexagonrpcd-v5', 'samurai-hexagonrpcd'],
            capture_output=True).stdout.strip(), 'Another file service is running')
    run(['modprobe', 'socinfo'], 'modules-private.log')
    require(text('/sys/devices/soc0/soc_id') == '339', 'Unexpected SoC')
    debug = Path('/sys/kernel/debug/qcom_socinfo')
    require([text(debug / p) for p in ['hardware_platform', 'hardware_platform_subtype',
            'platform_version']] == ['8', '0', '65536'], 'Unexpected hardware platform')
    check_hash(DAEMON, DAEMON_HASH)
    check_hash(LIBRARY, LIBRARY_HASH)
    run(['sha256sum', '-c', config['firmware_manifest']], 'firmware-check-private.log')
    prepare_root(config)
    record = {'boot_id': text(BOOT), 'started': False, 'attempted': True,
              'original_firmware': text(node / 'firmware'),
              'original_recovery': text(node / 'recovery')}
    save(record)  # Never retry a partly completed transition after an exception.
    try:
        write_node(node / 'firmware', FW)
        write_node(node / 'recovery', 'disabled')
        write_node(POWER, '1')
        require(text(POWER) == 'vdd=1 vddio=1', 'Sensor supply did not enable')
        write_node(node / 'state', 'start')
        require(text(node / 'state') == 'running', 'SLPI did not start')
        run(['modprobe', 'fastrpc'], 'modules-private.log')
        deadline = time.monotonic() + 12
        while not Path('/dev/fastrpc-sdsp').exists() and time.monotonic() < deadline:
            time.sleep(.1)
        require(Path('/dev/fastrpc-sdsp').is_char_device(), 'No SDSP FastRPC device')
        with (CONTROL / 'hexagonrpcd-private.log').open('ab') as log:
            daemon = subprocess.Popen([str(DAEMON), '-f', '/dev/fastrpc-sdsp', '-d', 'sdsp',
                '-R', str(CONTROL / 'root'), '-s'], stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True)
        identity = process_identity(daemon.pid)
        # exec can race the first /proc read; wait briefly for the pinned executable.
        for _ in range(50):
            if identity and identity['exe'] == str(DAEMON):
                break
            time.sleep(.02)
            identity = process_identity(daemon.pid)
        require(identity is not None and identity['exe'] == str(DAEMON), 'File server failed to exec')
        record.update(pid=daemon.pid, start_ticks=identity['start_ticks'])
        save(record)
        time.sleep(20)
        returncode = daemon.poll()
        alive_and_owned = owned_process(record)
        if returncode is not None or not alive_and_owned:
            record['readiness_failure'] = {
                'daemon_returncode': returncode,
                'owned_process': alive_and_owned,
                'slpi_state': text(node / 'state'),
            }
            save(record)
        require(alive_and_owned and returncode is None,
                'File server readiness failed; exit=' + str(returncode))
        env = dict(os.environ, LD_LIBRARY_PATH=str(LIBRARY.parent), LIBSSC_LIGHT_DATA_TYPE='wise_light')
        # A registered driver alone is insufficient: require a real measurement and clean disable.
        for sensor, label in [('accelerometer', 'Accelerometer'), ('light', 'Light')]:
            name = sensor + '-readiness-private.log'
            run(['ssccli', '--debug', '--sensor', sensor, '--timeout', '2'], name, 20, env)
            data = (CONTROL / name).read_text(errors='replace')
            require(label + ' sensor measurement:' in data and
                    (label + ' sensor disabled').lower() in data.lower(), 'No SSC readiness measurement')
        record.update(started=True)
        save(record)
    except Exception:
        try:
            stop(record, node)
        except Exception as cleanup:
            (CONTROL / 'cleanup-error-private.txt').write_text(str(cleanup) + '\n')
        raise


def main():
    os.umask(0o077)
    require(os.geteuid() == 0, 'Root required')
    require(len(sys.argv) == 2 and sys.argv[1] in ['start', 'stop', 'status'], 'Use start, stop or status')
    CONTROL.mkdir(mode=0o700, exist_ok=True)
    with (CONTROL / 'lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        nodes = [p for p in Path('/sys/class/remoteproc').glob('remoteproc*') if text(p / 'name') == 'slpi']
        require(len(nodes) == 1, 'Expected one SLPI remote processor')
        node = nodes[0]
        record = json.loads((CONTROL / 'state.json').read_text()) if (CONTROL / 'state.json').exists() else {}
        action = sys.argv[1]
        if action == 'start':
            start(json.loads(CONFIG.read_text()), record, node)
        elif action == 'stop':
            stop(record, node)
        else:
            require(record.get('started') and record['boot_id'] == text(BOOT)
                    and owned_process(record) and text(node / 'state') == 'running', 'SSC service stopped or unhealthy')
        print('Samurai SSC ' + action + ' succeeded')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
