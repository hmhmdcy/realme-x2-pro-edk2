"""Compile every CAMSS backend after the common CSID error-return change."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel280')
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD = Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
suffix = '-final' if sys.argv[1:] == ['final'] else ''
assert not sys.argv[1:] or sys.argv[1:] == ['final']
marker = PRIVATE / ('ipp' + suffix + '-build-state-private.json')
log = BUILD / ('ipp280' + suffix + '-werror-private.log')
assert not marker.exists() and not log.exists()
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='280',
           KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai')
command = ['make', '-C', str(TREE), 'O=' + str(BUILD), 'ARCH=arm64',
           'CROSS_COMPILE=aarch64-linux-gnu-', '-j3', 'W=1', 'KCFLAGS=-Werror',
           'drivers/media/platform/qcom/camss/qcom-camss.o', 'qcom/sm8150-samurai.dtb']
started = time.monotonic()
state = dict(stage=280, pid=os.getpid(), terminal=False, command=command)
with log.open('xb') as output:
    child = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT)
    state['child_pid'] = child.pid
    marker.write_text(json.dumps(state, indent=2) + '\n')
    code = child.wait()
state.update(terminal=True, exit=code, seconds=round(time.monotonic() - started, 2))
marker.write_text(json.dumps(state, indent=2) + '\n')
assert code == 0, 'Inspect the terminal build log before any follow-up'
diagnostics = [line for line in log.read_text(errors='replace').splitlines()
               if 'warning:' in line.lower() or 'error:' in line.lower()]
assert not diagnostics, diagnostics
obj = BUILD / 'drivers/media/platform/qcom/camss/qcom-camss.o'
dtb = BUILD / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
report = dict(stage=280, **{key:value for key,value in state.items() if key not in ['pid','child_pid','stage']},
              diagnostics=diagnostics, camera_component_objects=30,
              camss_object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
              dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),
              no_full_kernel_link_or_hardware_ipp_test=True, not_deployed=True)
(ROOT / ('ipp' + suffix + '-build-validation.json')).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
