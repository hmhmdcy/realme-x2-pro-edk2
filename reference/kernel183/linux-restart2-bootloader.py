#!/usr/bin/env python3
"""Use the audited Linux reboot path after quiescing/disabling the EUD console.

Only the EUD CSR_EUD_EN register used by drivers/tty/serial/eud.c is written.
--inspect validates the current boot and reads this register without unbinding.
"""
from pathlib import Path
import ctypes
import errno
import fcntl
import json
import mmap
import os
import struct
import sys
import time

assert os.getuid() == 0 and os.uname().machine == 'aarch64'
effective = next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:'))
assert int(effective, 16) & (1 << 22)  # CAP_SYS_BOOT from Linux uapi/capability.h
assert os.uname().version.startswith('#181 ')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k183-preflash/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert Path('/run/k183-bootloader-state').read_text().strip() == 'FROZEN'
assert all(Path('/sys/class/remoteproc/remoteproc%d/state' % n).read_text().strip() == 'offline' for n in range(3))
assert not Path('/proc/asound/card0').exists()
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text()
assert len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines()) == 1
assert Path('/sys/devices/platform/sensor-power/state').read_text().strip() == 'vdd=0 vddio=0'
for addr in ('1-0039', '1-003a'):
    assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices/' + addr + '/status').read_text()

device = Path('/sys/bus/platform/devices/88e0000.serial')
assert device.joinpath('driver').resolve() == Path('/sys/bus/platform/drivers/qcom_eud_com')
reg = device.joinpath('of_node/reg').read_bytes()
assert reg == struct.pack('>IIII', 0, 0x088e0000, 0, 0x2000)
assert device.joinpath('of_node/compatible').read_bytes() == b'qcom,sm8150-eud-com\0'
assert os.sysconf('SC_PAGE_SIZE') == 4096
fd = os.open('/dev/mem', os.O_RDWR | os.O_SYNC)
try:
    csr = mmap.mmap(fd, 4096, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ | mmap.PROT_WRITE, offset=0x088e1000)
    try:
        before = struct.unpack_from('<I', csr, 0x14)[0]
        assert (before & 0xff) in (0, 1), hex(before)
        if sys.argv[1:] == ['--inspect']:
            print(json.dumps({'stage': 183, 'current_boot_guard_pass': True, 'inspect_only': True,
                              'eud_csr_en_low_byte': before & 0xff}), flush=True)
            sys.exit(0)
        assert not sys.argv[1:]
        phase_path = Path('/run/k183-linux-restart2-phase-private.json')
        assert not phase_path.exists(), 'Do not repeat an unconfirmed restart operation'
        rootfd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            try:
                fcntl.ioctl(rootfd, 0xc0045877, 0)  # FIFREEZE from Linux uapi/fs.h
                frozen = 'new_freeze_confirmed'
            except OSError as error:
                assert error.errno == errno.EBUSY, error
                frozen = 'already_frozen_confirmed'
        finally:
            os.close(rootfd)
        report = dict(stage=183, phase='validated-current-linux', current_boot_guard_pass=True,
                      all_remoteprocs_offline=True, pcm_absent_and_amps_muted=True,
                      drm_inactive=True, sensor_supplies_off=True, taint=0,
                      root_freeze=frozen, restart2_command='bootloader', request_count=1)
        phase_path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
        time.sleep(0.5)
        Path('/sys/bus/platform/drivers/qcom_eud_com/unbind').write_text('88e0000.serial\n')
        assert not device.joinpath('driver').exists()
        report['eud_console_unbound'] = True
        # Match eud_reboot_cmd: retire console, disable EUD, read back, restart.
        struct.pack_into('<I', csr, 0x14, 0)
        after = struct.unpack_from('<I', csr, 0x14)[0]
        assert after & 0xff == 0, hex(after)
        report['eud_csr_disabled_readback'] = True
        report['phase'] = 'before-single-restart2'
        phase_path.write_text(json.dumps(report, indent=2) + '\n')
    finally:
        csr.close()
finally:
    os.close(fd)

assert boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
print(json.dumps(report), flush=True)
time.sleep(0.5)  # Allow the SSH submission receipt to reach the host before USB stops.
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
libc.syscall.argtypes = [ctypes.c_long, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
command = ctypes.create_string_buffer(b'bootloader\0')
result = libc.syscall(142, 0xfee1dead, 672274793, 0xa1b2c3d4, ctypes.cast(command, ctypes.c_void_p))
raise RuntimeError('restart2 returned: result=%d errno=%d; inspect state before further action' % (result, ctypes.get_errno()))
