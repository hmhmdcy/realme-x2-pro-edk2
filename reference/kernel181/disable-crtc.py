from pathlib import Path
import ctypes, os, subprocess, time

out = Path('/var/lib/samurai/k181-quiesce')
assert os.uname().version.startswith('#180 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (out/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
log = subprocess.check_output(['dmesg'],text=True)
assert log.count('Oops:') == 0 and log.count('WARNING:') == 0
assert subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode == 1
assert len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines()) == 1
assert Path('/sys/class/vtconsole/vtcon1/bind').read_text().strip() == '0'
for n in range(3): assert Path('/sys/class/remoteproc/remoteproc%d/state'%n).read_text().strip() == 'offline'
# A null modeset is safe even if the console is already inactive.
# Prevent fbdev's last-close callback from restoring the console modeset.
emulation = Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation')
assert emulation.read_text().strip() == 'Y'
emulation.write_text('N\n')
assert emulation.read_text().strip() == 'N'
lib = ctypes.CDLL('libdrm.so.2',use_errno=True)
lib.drmSetMaster.argtypes = [ctypes.c_int]
lib.drmModeSetCrtc.argtypes = [ctypes.c_int,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
fd = os.open('/dev/dri/card1',os.O_RDWR|os.O_CLOEXEC)
try:
    assert lib.drmSetMaster(fd) == 0, ctypes.get_errno()
    result = lib.drmModeSetCrtc(fd,91,0,0,0,None,0,None)
    (out/'explicit-crtc-disable.txt').write_text('result=%d errno=%d\n'%(result,ctypes.get_errno()))
    assert result == 0, ctypes.get_errno()
finally:
    os.close(fd)
for n in range(3):
    state = Path('/sys/kernel/debug/dri/1/state').read_text()
    (out/('drm-explicit-disable-%d.txt'%n)).write_text(state)
    assert 'active=1' not in state
    time.sleep(1)
print('K181_EXPLICIT_CRTC_DISABLE_VERIFIED',flush=True)
