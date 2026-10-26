from pathlib import Path
import hashlib, json, shutil, subprocess
import host
HERE = Path(__file__).resolve().parent
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
tree = '/work/libcamera299-inline'
stage = SDK / 'private/camss303-contract'
shutil.copyfile(HERE / 'serializer-contract.cpp', stage / 'serializer.cpp')
q = subprocess.run(['chroot', str(SDK), '/usr/bin/g++', '-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror', '-DLIBCAMERA_BASE_PRIVATE',
 '-I' + tree + '/include', '-I' + tree + '/output/include', '/private/camss303-contract/serializer.cpp',
 '-L' + tree + '/output/src/libcamera', '-L' + tree + '/output/src/libcamera/base', '-Wl,-rpath-link,' + tree + '/output/src/libcamera/base',
 '-lcamera', '-lcamera-base', '-o', '/private/camss303-contract/serializer'], capture_output=True, timeout=180)
(host.PRIVATE / 'serializer-compile-private.log').write_bytes(q.stdout + q.stderr)
assert q.returncode == 0, q.stderr.decode()
q = subprocess.run(['chroot', str(SDK), '/usr/bin/env', 'LD_LIBRARY_PATH=' + tree + '/output/src/libcamera:' + tree + '/output/src/libcamera/base',
 '/private/camss303-contract/serializer'], capture_output=True, timeout=20)
(host.PRIVATE / 'serializer-private.log').write_bytes(q.stdout + q.stderr)
print((q.stdout + q.stderr).decode())
report = dict(stage=303, aarch64_werror_compile=True, passed=q.returncode == 0 and b'SERIALIZER_PASS cases=4' in q.stdout,
              hardware_verified=False, isolated_ipc_verified=False,
              source_sha256=hashlib.sha256((HERE / 'serializer-contract.cpp').read_bytes()).hexdigest())
(HERE / 'serializer-validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert report['passed']
