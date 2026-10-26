"""Fixed-board inspection/staging. Run only in an explicitly owned window.

snapshot and shadow actions do not write MP2650 configuration. The diagnostic
MAC selectors used by the kernel providers remain read-only gauge commands.
"""
from pathlib import Path
import ctypes as C
import errno
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/root/charging-management-20261023')
CLIENT = Path('/sys/bus/i2c/devices/0-005c')
PSY = Path('/sys/class/power_supply')
REGS = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x07, 0x08, 0x09, 0x0f, 0x13]

def read(p):
    try: return Path(p).read_text().strip()
    except OSError as e: return {'errno': e.errno}

def run(*args):
    q = subprocess.run(args, capture_output=True, text=True)
    if q.returncode: raise RuntimeError([args, q.returncode, q.stdout, q.stderr])
    return q.stdout.strip()

class Msg(C.Structure):
    _fields_ = [('addr', C.c_ushort), ('flags', C.c_ushort),
                ('length', C.c_ushort), ('buf', C.c_void_p)]
class Transfer(C.Structure):
    _fields_ = [('msgs', C.POINTER(Msg)), ('nmsgs', C.c_uint)]

def registers():
    libc = C.CDLL(None, use_errno=True)
    fd = os.open('/dev/i2c-0', os.O_RDWR | os.O_CLOEXEC)
    values = {}
    try:
        for reg in REGS:
            tx, rx = C.create_string_buffer(bytes([reg])), C.create_string_buffer(1)
            msgs = (Msg * 2)(Msg(0x5c, 0, 1, C.cast(tx, C.c_void_p)),
                             Msg(0x5c, 1, 1, C.cast(rx, C.c_void_p)))
            ret = libc.ioctl(fd, 0x0707, C.byref(Transfer(msgs, 2)))
            if ret != 2: raise OSError(C.get_errno() if ret < 0 else errno.EIO, 'read charger')
            values[f'{reg:02x}'] = rx.raw[0]
    finally: os.close(fd)
    return values

def state():
    services = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        comm = read(proc / 'comm')
        if isinstance(comm, str) and comm in ['phosh','weston','phoc','pipewire','wireplumber']:
            services.append({'pid': int(proc.name), 'comm': comm, 'uid': proc.stat().st_uid})
    return {'boot_id': read('/proc/sys/kernel/random/boot_id'),
        'release': os.uname().release, 'taint': read('/proc/sys/kernel/tainted'),
        'driver': CLIENT.joinpath('driver').resolve().name,
        'registers': registers(),
        'camera_pm': {n: read(Path('/sys/bus/platform/devices') / n / 'power/runtime_status')
            for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},
        'm2m': read('/sys/bus/platform/devices/ac10000.icp/m2m_status'),
        'services': services,
        'supplies': {p.name: read(p / 'uevent') for p in PSY.iterdir()}}

def guard():
    assert os.geteuid() == 0
    assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k363+'
    assert read('/proc/sys/kernel/tainted') == '0'
    assert CLIENT.joinpath('name').read_text().strip() == 'mp2650'
    assert CLIENT.joinpath('of_node').resolve().as_posix().endswith('/soc@0/geniqup@8c0000/i2c@884000/charger@5c')
    if (ROOT / 'original-private.json').exists():
        assert read('/proc/sys/kernel/random/boot_id') == json.loads((ROOT / 'original-private.json').read_text())['boot_id']

def bind(driver, action):
    Path('/sys/bus/i2c/drivers', driver, action).write_text('0-005c')

def configuration(data):
    return {k: v for k,v in data['registers'].items() if k != '13'}

def shadow():
    assert CLIENT.joinpath('driver').resolve().name == 'mp2650'
    for name in ['samurai_usb_input', 'samurai_gauge_protection', 'samurai_mp2650']:
        assert not Path('/sys/module', name).exists()
    before = state()
    (ROOT / 'shadow-before-private.json').write_text(json.dumps(before))
    # Reject duplicate supplies. No fallback to a name that may hide another driver.
    assert not (PSY / 'samurai-usb-input').exists()
    assert not (PSY / 'samurai-gauge-protection').exists()
    changed = False
    try:
        run('insmod', str(ROOT / 'samurai-usb-input.ko'), 'register_board=1')
        assert (PSY / 'samurai-usb-input').exists()
        run('insmod', str(ROOT / 'samurai-gauge-protection.ko'), 'register_board=1')
        assert (PSY / 'samurai-gauge-protection').exists()
        bind('mp2650', 'unbind'); changed = True
        run('insmod', str(ROOT / 'samurai-mp2650.ko'), 'runtime_board=1', 'control=0')
        assert CLIENT.joinpath('driver').resolve().name == 'samurai-mp2650'
        time.sleep(3)
        observed = state()
        observed['telemetry'] = read(CLIENT / 'telemetry')
        observed['protection'] = read('/sys/devices/platform/samurai-gauge-protection/protection_state')
        (ROOT / 'shadow-captured-private.json').write_text(json.dumps(observed))
        assert configuration(observed) == configuration(before), 'shadow changed charger registers'
        assert observed['taint'] == '0'
        return observed
    finally:
        if Path('/sys/module/samurai_mp2650').exists(): run('rmmod','samurai_mp2650')
        if changed and not CLIENT.joinpath('driver').exists(): bind('mp2650','bind')
        if Path('/sys/module/samurai_gauge_protection').exists(): run('rmmod','samurai_gauge_protection')
        if Path('/sys/module/samurai_usb_input').exists(): run('rmmod','samurai_usb_input')
        after = state()
        (ROOT / 'shadow-restored-private.json').write_text(json.dumps(after))
        assert after['driver'] == 'mp2650' and after['taint'] == '0'
        assert configuration(after) == configuration(before), 'configuration mismatch after shadow'
        assert after['services'] == before['services'], 'session service change'
        assert after['camera_pm'] == before['camera_pm'] and after['m2m'] == before['m2m'], 'camera state change'

if __name__ == '__main__':
    guard()
    action = sys.argv[1]
    if action == 'snapshot':
        data = state()
        target = ROOT / 'original-private.json'
        if not target.exists(): target.write_text(json.dumps(data))
        else: assert configuration(json.loads(target.read_text())) == configuration(data)
    elif action == 'shadow': data = shadow()
    elif action == 'state': data = state()
    else: raise ValueError(action)
    print(json.dumps(data))
