"""Final W=1/-Werror ARM64 object build with explicit process/terminal evidence."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD = Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
assert not (PRIVATE / 'final-build-state-private.json').exists()
log = BUILD / 'final-werror-private.log'
assert not log.exists()
command = ['make', '-C', str(TREE), 'O=' + str(BUILD), 'ARCH=arm64',
           'CROSS_COMPILE=aarch64-linux-gnu-', '-j3', 'W=1', 'KCFLAGS=-Werror',
           'drivers/media/platform/qcom/camss/qcom-camss.o',
           'drivers/media/v4l2-core/v4l2-ioctl.o', 'drivers/media/v4l2-core/v4l2-isp.o',
           'qcom/sm8150-samurai.dtb']
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='279',
           KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai')
state = dict(stage=279, terminal=False, pid=os.getpid(),
             start_ticks=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
             command=command, phone_unchanged=True)
marker = PRIVATE / 'final-build-state-private.json'
started = time.monotonic()
with log.open('xb') as output:
    child = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT)
    state['child_pid'] = child.pid
    marker.write_text(json.dumps(state, indent=2) + '\n')
    code = child.wait()
state.update(terminal=True, exit_code=code, seconds=round(time.monotonic() - started, 2))
marker.write_text(json.dumps(state, indent=2) + '\n')
assert code == 0, 'Inspect terminal build log before resuming'
diagnostics = [line for line in log.read_text(errors='replace').splitlines()
               if 'warning:' in line.lower() or 'error:' in line.lower()]
assert not diagnostics, diagnostics
artifacts = {}
for name in ['drivers/media/platform/qcom/camss/qcom-camss.o',
             'drivers/media/v4l2-core/v4l2-ioctl.o', 'drivers/media/v4l2-core/v4l2-isp.o',
             'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']:
    path = BUILD / name
    artifacts[name] = dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
objdir = BUILD / 'drivers/media/platform/qcom/camss'
objects = [path for path in objdir.glob('*.o') if path.name != 'qcom-camss.o']
subprocess.run(['git', '-C', str(TREE), 'diff', '--check'], check=True)
report = dict(stage=279, command=command, exit=code, seconds=state['seconds'],
              camera_backend_objects=len(objects), diagnostics=diagnostics, artifacts=artifacts,
              full_kernel_module_link_or_runtime_not_tested=True,
              vfe170_pixel_pipeline_not_enabled=True, phone_unchanged=True)
(ROOT / 'candidate-build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
