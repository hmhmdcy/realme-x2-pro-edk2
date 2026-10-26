from pathlib import Path
import os
import resource
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel180')
log = out / 'first-objects-w1-private.log'
assert not log.exists()
env = os.environ.copy()
env.update(PATH='/home/cy122/.cargo/bin:' + env['PATH'], RUSTUP_HOME='/home/cy122/.rustup',
           KBUILD_BUILD_VERSION='180')
def limit():
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
with log.open('wb') as stream:
    result = subprocess.run(['make', 'ARCH=arm64', 'CROSS_COMPILE=aarch64-linux-gnu-',
                             'LD=aarch64-linux-gnu-ld --no-keep-memory', 'W=1', '-j4',
                             'drivers/soc/qcom/pdr_interface.o', 'drivers/mfd/wcd934x.o'],
                            cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT,
                            preexec_fn=limit)
print('OBJECT_BUILD_EXIT', result.returncode)
diagnostics = [line for line in log.read_text().splitlines()
               if 'warning:' in line or 'error:' in line]
print('\n'.join(diagnostics))
assert result.returncode == 0 and not diagnostics
