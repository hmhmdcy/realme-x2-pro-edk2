"""Build all CAMSS backends and changed V4L2 core in a fresh ARM64 output tree."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD = Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279')
assert not BUILD.exists(), 'Inspect the live/terminal build before resuming'
BUILD.mkdir(mode=0o700)
source = Path('/home/cy122/x2pro-linux/camera276-build-r1/.config')
assert source.is_file()
shutil.copyfile(source, BUILD / '.config')
subprocess.run([str(TREE / 'scripts/config'), '--file', str(BUILD / '.config'),
                '--set-str', 'LOCALVERSION', '-rmx1931-samurai-k279candidate',
                '--disable', 'LOCALVERSION_AUTO', '--set-str', 'INITRAMFS_SOURCE', ''], check=True)
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='279',
           KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai')
command = ['make', '-C', str(TREE), 'O=' + str(BUILD), 'ARCH=arm64',
           'CROSS_COMPILE=aarch64-linux-gnu-', '-j3']
state = dict(stage=279, candidate=str(TREE), build=str(BUILD), pid=os.getpid(),
             start_ticks=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
             terminal=False, steps=[], phone_unchanged=True)
marker = PRIVATE / 'candidate-build-state-private.json'


def save():
    marker.write_text(json.dumps(state, indent=2) + '\n')


save()
try:
    for name, args in [('configure', ['olddefconfig']),
                       ('prepare', ['modules_prepare']),
                       ('camss-v4l2', ['W=1', 'drivers/media/platform/qcom/camss/qcom-camss.o',
                                      'drivers/media/v4l2-core/v4l2-ioctl.o',
                                      'drivers/media/v4l2-core/v4l2-isp.o'])]:
        started = time.monotonic()
        log = BUILD / (name + '-private.log')
        with log.open('xb') as output:
            child = subprocess.Popen(command + args, env=env, stdout=output, stderr=subprocess.STDOUT)
            state.update(step=name, child_pid=child.pid)
            save()
            code = child.wait()
        state['steps'].append(dict(step=name, exit=code, seconds=round(time.monotonic() - started, 2)))
        save()
        assert code == 0, 'Inspect ' + str(log)
    state.update(terminal=True, exit_code=0)
except BaseException:
    state.update(terminal=True, exit_code=1)
    save()
    raise
save()
print(json.dumps(state, indent=2), flush=True)
