from pathlib import Path
import ctypes, os, subprocess, time

out = Path('/var/lib/samurai/k174-recovery-quiesce')
assert os.uname().version.startswith('#172 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (out/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '128'
log = subprocess.check_output(['dmesg'],text=True)
assert log.count('Oops:') == 1 and 'regmap_name_read_file+0x54' in log
assert subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode == 1
assert len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines()) == 1
assert Path('/sys/class/vtconsole/vtcon1/bind').read_text().strip() == '0'
for n in range(3): assert Path('/sys/class/remoteproc/remoteproc%d/state'%n).read_text().strip() == 'offline'
assert 'active=1' in Path('/sys/kernel/debug/dri/1/state').read_text()
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
subprocess.run(['python3','/tmp/k174-recovery-check-quiesce.py','--record'],check=True)
subprocess.run(['sync'],check=True)
subprocess.run(['tar','-C',str(out),'-cf','/tmp/k174-recovery-quiesce-private.tar','.'],check=True)
print('K174_RECOVERY_CRTC_DISABLED_QUIESCE_VALIDATED',flush=True)
