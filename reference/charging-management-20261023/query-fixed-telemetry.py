"""Fixed OEM/TI telemetry only. No charger/protection configuration writes."""
from pathlib import Path
import ctypes as C
import errno
import json
import os
import re
import time

assert os.geteuid() == 0
assert os.uname().release == '7.3.0-rc6-rmx1931-samurai-k363+'
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
gauge = Path('/sys/bus/i2c/devices/5-0055')
assert gauge.joinpath('name').read_text().strip() == 'bq28z610'
assert gauge.joinpath('driver').resolve().name == 'bq27xxx-battery'
assert gauge.joinpath('of_node').resolve() == Path('/sys/firmware/devicetree/base/soc@0/geniqup@cc0000/i2c@c94000/fuel-gauge@55')
# The current matched source/config disables bq27xxx NVM updates. Existing
# standard-word polling does not select MAC commands. Echo/checksum/length
# reject interference. This diagnostic does not unbind that driver.
class Msg(C.Structure):
    _fields_ = [('addr', C.c_ushort), ('flags', C.c_ushort),
                ('length', C.c_ushort), ('buf', C.c_void_p)]
class Transfer(C.Structure):
    _fields_ = [('msgs', C.POINTER(Msg)), ('nmsgs', C.c_uint)]
libc = C.CDLL(None, use_errno=True)
libc.ioctl.restype = C.c_int
transfers = []

def xfer(fd, addr, write, length=0):
    tx = C.create_string_buffer(bytes(write))
    rx = C.create_string_buffer(length) if length else None
    msgs = (Msg * (2 if length else 1))()
    msgs[0] = Msg(addr, 0, len(write), C.cast(tx, C.c_void_p))
    if length:
        msgs[1] = Msg(addr, 1, length, C.cast(rx, C.c_void_p))
    arg = Transfer(msgs, len(msgs))
    ret = libc.ioctl(fd, 0x0707, C.byref(arg))
    transfers.append({'address': addr, 'write_hex': bytes(write).hex(),
                      'read_bytes': length, 'return': ret, 'errno': C.get_errno() if ret < 0 else 0})
    if ret < 0:
        raise OSError(C.get_errno(), os.strerror(C.get_errno()))
    if ret != len(msgs):
        raise OSError(errno.EIO, 'partial I2C_RDWR')
    return rx.raw if rx else b''

fd = os.open('/dev/i2c-5', os.O_RDWR | os.O_CLOEXEC)
result = {'gauge': {}, 'short_ic': {}, 'pmic': {}, 'transactions': transfers}
try:
    result['standard_words'] = {hex(reg): int.from_bytes(xfer(fd, 0x55, [reg], 2), 'little')
                               for reg in [0x06, 0x08, 0x0a, 0x14]}
    # Only read-only MAC commands from TI table12-2 and the OEM query path.
    for cmd in [0x0001, 0x0002, 0x0051, 0x0053, 0x0054, 0x0057, 0x0071]:
        xfer(fd, 0x55, [0x3e, cmd & 255, cmd >> 8])
        time.sleep(0.002)
        raw = xfer(fd, 0x55, [0x3e], 36)
        length = raw[35]
        checksum_ok = 5 <= length <= 36 and ((sum(raw[:length-2]) + raw[34]) & 255) == 255
        row = {'raw_hex': raw.hex(), 'echo': int.from_bytes(raw[:2], 'little'),
               'length': length, 'checksum_ok': checksum_ok}
        row['valid'] = row['echo'] == cmd and checksum_ok
        result['gauge'][hex(cmd)] = row
        # A malformed response is evidence, not a reason to reset/unseal.
        if not row['valid']:
            break
    if not Path('/sys/bus/i2c/devices/5-0058').exists():
        try:
            # Unowned address: ordinary I2C_SLAVE checks, no FORCE request.
            if libc.ioctl(fd, 0x0703, 0x58) < 0:
                raise OSError(C.get_errno(), 'I2C_SLAVE')
            chip_id = xfer(fd, 0x58, [0x00], 1)[0]
            result['short_ic']['id'] = chip_id
            if chip_id & 0xf0 in [0xd0, 0xe0, 0xf0]:
                result['short_ic']['registers'] = {hex(reg): xfer(fd, 0x58, [reg], 1)[0]
                                                  for reg in [0x02, 0x03, 0x08]}
        except OSError as e:
            result['short_ic']['error'] = {'errno': e.errno, 'message': str(e)}
finally:
    os.close(fd)

regmap = Path('/sys/kernel/debug/regmap/0-02')
try:
    assert regmap.joinpath('name').read_text().strip() == 'pmic-spmi'
    assert regmap.joinpath('range').read_text() == '0-ffff\n'
    fd = os.open(regmap / 'registers', os.O_RDONLY | os.O_CLOEXEC)
    try:
        for reg in [0x1307, 0x1308, 0x1310, 0x1506, 0x1509, 0x150b, 0x150d]:
            line = os.pread(fd, 9, reg * 9)
            match = re.fullmatch(rb'([0-9a-f]{4}): ([0-9a-f]{2})\n', line)
            assert match and int(match[1], 16) == reg
            result['pmic'][hex(reg)] = int(match[2], 16)
    finally:
        os.close(fd)
except (OSError, AssertionError) as e:
    result['pmic_error'] = str(e)
result['configuration_data_writes'] = 0
result['taint_after'] = Path('/proc/sys/kernel/tainted').read_text().strip()
print(json.dumps(result))
