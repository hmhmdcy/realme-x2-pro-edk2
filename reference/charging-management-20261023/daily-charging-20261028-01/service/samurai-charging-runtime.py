#!/usr/bin/python3
"""Self-contained board service; the kernel owns the charging state machine."""
from pathlib import Path
import errno
import fcntl
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
import traceback

MANIFEST = Path('/usr/share/samurai-charging/manifest.json')
STATE = Path('/var/lib/samurai/charging-managed')
CLIENT = Path('/sys/bus/i2c/devices/0-005c')
PSY = Path('/sys/class/power_supply/mp2650-input')
USB = Path('/sys/class/power_supply/samurai-usb-input')
TYPEC_GLOB = '/sys/class/power_supply/tcpm-source-psy-*'
USB_MODULE = 'samurai_usb_input'
MP_MODULE = 'samurai_mp2650'


def run(*argv):
    subprocess.run(argv, check=True)


def read_int(path):
    return int(path.read_text().strip())


def optional_int(path):
    try:
        return read_int(path)
    except (OSError, ValueError):
        return None


def loaded_matches(path, name):
    raw = path.read_bytes()
    off = struct.unpack_from('<Q', raw, 40)[0]
    stride, count, strings = struct.unpack_from('<HHH', raw, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, off + i * stride)
                for i in range(count)]
    names = raw[sections[strings][4]:sections[strings][4] +
                sections[strings][5]]
    note = next(s for s in sections
                if names[s[0]:].split(b'\0')[0] == b'.note.gnu.build-id')
    note_path = Path('/sys/module', name, 'notes/.note.gnu.build-id')
    assert note_path.read_bytes() == raw[note[4]:note[4] + note[5]]


def verify():
    assert os.geteuid() == 0
    compatible = Path('/sys/firmware/devicetree/base/compatible').read_bytes()
    assert b'realme,samurai' in compatible.split(b'\0')
    meta = json.loads(MANIFEST.read_text())
    assert os.uname().release == meta['release']
    for path, digest in meta['installed_files'].items():
        p = Path(path)
        assert p.is_file() and not p.is_symlink()
        assert p.stat().st_uid == 0 and not p.stat().st_mode & 0o022
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, path
    return meta


def install_hashes():
    meta = json.loads(MANIFEST.read_text())
    actual = {}
    for path in meta['installed_files']:
        actual[path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return actual


def load_module(meta, name, args=()):
    path = Path(meta['modules'][name]['target'])
    module = name.replace('-', '_')
    if Path('/sys/module', module).exists() and args and name == 'samurai-mp2650':
        for arg in args:
            param, expected = arg.split('=', 1)
            actual = module_param(module, param)
            if actual is None:
                raise RuntimeError(f'{name} has no parameter {param}')
            if actual in ('Y', '1', 'y', 'true', 'on'):
                actual = '1'
            if expected in ('Y', '1', 'y', 'true', 'on'):
                expected = '1'
            if actual != expected:
                if driver_name() == 'samurai-mp2650':
                    unbind_managed()
                run('rmmod', module)
                break
    if Path('/sys/module', module).exists():
        try:
            loaded_matches(path, module)
        except AssertionError:
            if name != 'samurai-mp2650':
                raise RuntimeError(f'{name} is loaded from a different build')
            if driver_name() == 'samurai-mp2650':
                (CLIENT / 'driver' / 'unbind').write_text('0-005c\n')
            run('rmmod', MP_MODULE)
    if not Path('/sys/module', module).exists():
        run('insmod', str(path), *args)
    loaded_matches(path, module)


def release_managed():
    """Return the client to the built-in input observer without charging."""
    if driver_name() != 'samurai-mp2650':
        return
    unbind_managed()
    Path('/sys/bus/i2c/drivers/mp2650/bind').write_text('0-005c\n')
    assert driver_name() == 'mp2650', driver_name()


def unbind_managed():
    if driver_name() == 'samurai-mp2650':
        Path('/sys/bus/i2c/drivers/samurai-mp2650/unbind').write_text('0-005c\n')
    assert driver_name() is None, driver_name()


def module_param(name, param):
    try:
        return Path('/sys/module', name, 'parameters', param).read_text().strip()
    except OSError:
        return None


def sample():
    return {k: int(v) for k, v in
            (item.split('=', 1)
             for item in (CLIENT / 'telemetry').read_text().split())}


def driver_name():
    link = CLIENT / 'driver'
    return link.resolve().name if link.exists() else None


def supply_value(psy, name):
    path = psy / name
    return path.read_text().strip() if path.exists() else None


def wait_for_typec(timeout=60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        paths = list(Path('/sys/class/power_supply').glob(
            'tcpm-source-psy-*'))
        if paths:
            return paths[0]
        time.sleep(0.2)
    raise RuntimeError('Type-C source supply did not appear')


def wait_for_source_budget(timeout=60.0):
    """Return the conservative source ceiling after DWC3/TCPM come up.

    A default-Rp sink can expose a zero TCPM limit before any explicit PD
    contract. That means no negotiated contract, not a zero-amp source. Fall
    back to the board input provider's standard CURRENT_MAX or UDC/BC1.2
    INPUT_CURRENT_LIMIT; never invent a higher charging ceiling.
    """
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            online = read_int(USB / 'online')
            type_name = supply_value(USB, 'type')
            usb_max = optional_int(USB / 'current_max')
            usb_limit = optional_int(USB / 'input_current_limit')
            tcpm_max = None
            try:
                tcpm = wait_for_typec(0.1)
                tcpm_max = optional_int(tcpm / 'current_max')
            except RuntimeError:
                pass
        except (OSError, ValueError) as error:
            last = repr(error)
        else:
            source = next((value for value in
                           (tcpm_max, usb_max, usb_limit)
                           if value is not None and value >= 50000), None)
            if online == 0 or source is not None:
                return {
                    'usb_online': online,
                    'usb_current_max': usb_max,
                    'usb_input_current_limit': usb_limit,
                    'usb_type': type_name,
                    'tcpm_current_max': tcpm_max,
                    'source_current_ua': source or 0,
                }
            last = {
                'usb_online': online,
                'usb_current_max': usb_max,
                'usb_input_current_limit': usb_limit,
                'tcpm_current_max': tcpm_max,
            }
        time.sleep(0.25)
    raise RuntimeError(f'source budget unavailable: {last}')


def wait_for_managed_sample(timeout=30.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            data = sample()
        except (OSError, ValueError) as error:
            last = repr(error)
        else:
            common = (data.get('shadow') == 0 and data.get('managed') == 1
                    and data.get('providers') == 1 and data.get('valid') == 1
                    and data.get('source_inhibit') == 0
                    and data.get('latched') == 0
                    and data.get('stop_error') == 0
                    and data.get('fault') == 0
                    and 0 <= data.get('age_ms', -1) <= 3000)
            if data.get('online') == 1:
                ready = (common and data.get('protection_ok') == 1
                         and data.get('budget_ua', 0) >= 50000)
            else:
                ready = common
            if ready:
                return data
            last = data
        time.sleep(0.25)
    raise RuntimeError(f'managed charger did not become ready: {last}')


def bind_managed():
    if driver_name() == 'samurai-mp2650':
        return
    if driver_name() == 'mp2650':
        Path('/sys/bus/i2c/drivers/mp2650/unbind').write_text('0-005c\n')
    try:
        Path('/sys/bus/i2c/drivers/samurai-mp2650/bind').write_text('0-005c\n')
    except OSError:
        if driver_name() != 'samurai-mp2650':
            raise
    assert driver_name() == 'samurai-mp2650', driver_name()


def active_behaviour(text):
    for item in text.split():
        if item.startswith('[') and item.endswith(']'):
            return item[1:-1]
    return text.strip()


def safe_stop_sample(data):
    return (data.get('shadow') == 0 and data.get('valid') == 1
            and data.get('online') == 1 and data.get('protection_ok') == 1
            and data.get('source_inhibit') == 0
            and data.get('desired_enable') == 0
            and data.get('latched') == 0 and data.get('stop_error') == 0
            and data.get('fault') == 0 and data.get('cycle_timeout') == 0
            and 0 <= data.get('age_ms', -1) <= 3000 and 'flags' in data)


def request(name, value):
    try:
        (PSY / name).write_text(value)
    except OSError as error:
        data = sample()
        hold = (error.errno in (errno.EAGAIN, errno.ENODATA)
                and data.get('source_inhibit') == 1
                and not data.get('latched', 1)
                and not data.get('stop_error', 1)
                and not data.get('fault', 1)
                and not data.get('cycle_timeout', 1))
        if not hold:
            raise


def inhibit():
    try:
        (PSY / 'charge_behaviour').write_text('inhibit-charge')
    except OSError:
        pass
    time.sleep(0.2)
    data = sample()
    assert data['desired_enable'] == 0 and data['latched'] == 0
    assert data['stop_error'] == 0


def start(meta):
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    # The DT node is normally present, but request the synthetic provider as a
    # fallback when firmware omitted it. The module ignores duplicate probes.
    load_module(meta, 'samurai-usb-input', ('register_board=1',))
    load_module(meta, 'samurai-gauge-protection', ('register_board=1',))
    wait_for_typec()
    managed = driver_name() == 'samurai-mp2650'
    if managed:
        try:
            current = sample()
        except (OSError, ValueError):
            current = None
        managed = current is not None and current.get('shadow') == 0
        if not managed:
            unbind_managed()
    # A probe that raced ahead of the optional providers may have loaded the
    # module in shadow mode. Remove it before binding so ownership is computed
    # from the providers that are now present.
    if Path('/sys/module', MP_MODULE).exists():
        if driver_name() == 'samurai-mp2650':
            unbind_managed()
        run('rmmod', MP_MODULE)
    load_module(meta, 'samurai-mp2650', ('runtime_board=1', 'control=1'))
    if module_param('samurai_mp2650', 'control') != 'Y':
        if driver_name() == 'samurai-mp2650':
            unbind_managed()
        run('rmmod', MP_MODULE)
        load_module(meta, 'samurai-mp2650', ('runtime_board=1', 'control=1'))
    bind_managed()
    data = wait_for_managed_sample()
    online = read_int(USB / 'online') == 1
    source = wait_for_source_budget() if online else {
        'usb_online': 0,
        'usb_current_max': optional_int(USB / 'current_max'),
        'usb_input_current_limit': optional_int(
            USB / 'input_current_limit'),
        'usb_type': supply_value(USB, 'type'),
        'tcpm_current_max': None,
        'source_current_ua': 0,
    }
    requested_input = min(source['source_current_ua'], 2000000) // 50000 * 50000
    if not online or requested_input < 50000:
        requested_input = 500000
    # Program the board ceilings once. The driver applies the live source
    # budget and derives a safe battery current dynamically on every sample.
    request('input_current_limit', '2000000')
    request('constant_charge_current', '1100000')
    request('charge_behaviour', 'auto')
    data = wait_for_managed_sample()
    effective_input = read_int(PSY / 'input_current_limit')
    effective_charge = read_int(PSY / 'constant_charge_current')
    behaviour = active_behaviour((PSY / 'charge_behaviour').read_text())
    charge_behaviour = (PSY / 'charge_behaviour').read_text().strip()
    limits = {
        'requested_input_current_limit': requested_input,
        'programmed_input_ceiling': 2000000,
        'programmed_charge_ceiling': 1100000,
        'effective_input_current_limit': effective_input,
        'constant_charge_current': effective_charge,
        'charge_behaviour': charge_behaviour,
        'active_charge_behaviour': behaviour,
    }
    assert behaviour == 'auto', limits
    if online:
        assert 50000 <= effective_input <= min(requested_input, 2000000), limits
        assert 200000 <= effective_charge <= 1100000, limits
    else:
        assert data['online'] == 0, data
    if online and effective_input != requested_input:
        run('sh', '-c',
            'printf "%s\\n" "source budget caps managed input request" > '
            '/dev/kmsg')
    return {
        'managed': True,
        'driver': 'samurai-mp2650',
        'source': source,
        'online': online,
        'limits': limits,
        'telemetry': data,
    }


def stop():
    if driver_name() == 'samurai-mp2650':
        inhibit()
        release_managed()
    return {'managed': False,
            'requested': 'inhibit-charge'}


def command(meta, action):
    if action == 'start':
        return start(meta)
    if action == 'stop':
        return stop()
    if action == 'status':
        driver = driver_name()
        if driver == 'samurai-mp2650':
            try:
                data = sample()
            except (OSError, ValueError):
                data = None
            if data is None or data.get('managed') != 1:
                return {'managed': False, 'driver': driver, 'sample': data}
            return {'managed': True, 'driver': driver, 'sample': data}
        return {'managed': False, 'driver': driver, 'sample': None}
    raise ValueError(action)


if __name__ == '__main__':
    os.umask(0o077)
    assert len(sys.argv) == 2
    fd = os.open('/run/lock/samurai-charging.lock',
                 os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        assert os.fstat(fd).st_uid == 0
        fcntl.flock(fd, fcntl.LOCK_EX)
        STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            if sys.argv[1] == 'hashes':
                result = install_hashes()
            else:
                result = command(verify(), sys.argv[1])
        except BaseException:
            failure = STATE / 'last-failure-private.txt'
            failure.write_text(traceback.format_exc())
            os.chmod(failure, 0o600)
            raise
        tmp = STATE / 'state-next-private.json'
        tmp.write_text(json.dumps(result, sort_keys=True))
        tmp.replace(STATE / 'state-private.json')
        print(json.dumps(result, sort_keys=True))
    finally:
        os.close(fd)
