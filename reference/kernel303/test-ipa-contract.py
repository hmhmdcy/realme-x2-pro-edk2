"""Compile and execute the actual AArch64 IPA DSO; QEMU is not a hardware test."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess
import host
HERE = Path(__file__).resolve().parent
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
tree = '/work/libcamera299-inline'
assert json.loads((HERE / 'build-validation.json').read_text())['build_exit'] == 0
stage = SDK / 'private/camss303-contract'
stage.mkdir(exist_ok=True)
for source, target in [(HERE / 'ipa-contract.cpp', 'contract.cpp'), (HERE / 'imx319-ae.yaml', 'ae.yaml'),
                       (HERE.parent / 'kernel302/imx319-manual.yaml', 'manual.yaml')]:
    shutil.copyfile(source, stage / target)
q = subprocess.run(['chroot', str(SDK), '/usr/bin/g++', '-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror', '-DLIBCAMERA_BASE_PRIVATE',
 '-I' + tree + '/include', '-I' + tree + '/output/include', '/private/camss303-contract/contract.cpp',
 '-L' + tree + '/output/src/libcamera', '-L' + tree + '/output/src/libcamera/base', '-Wl,-rpath-link,' + tree + '/output/src/libcamera/base',
 '-lcamera', '-lcamera-base', '-ldl', '-o', '/private/camss303-contract/contract'], capture_output=True, timeout=180)
(host.PRIVATE / 'contract-compile-private.log').write_bytes(q.stdout + q.stderr)
assert q.returncode == 0, q.stderr.decode()
q = subprocess.run(['chroot', str(SDK), '/usr/bin/env', 'LD_LIBRARY_PATH=' + tree + '/output/src/libcamera:' + tree + '/output/src/libcamera/base',
 '/private/camss303-contract/contract', tree + '/output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 '/private/camss303-contract/manual.yaml', '/private/camss303-contract/ae.yaml'], capture_output=True, timeout=60)
attempt = 1
while (host.PRIVATE / f'contract-r{attempt}-private.log').exists(): attempt += 1
(host.PRIVATE / f'contract-r{attempt}-private.log').write_bytes(q.stdout + q.stderr)
print((q.stdout + q.stderr).decode()[-6000:])
model = re.search(rb'AE_MODEL_PASS frames=(\d+) proposals=(\d+) held=(\d+)', q.stdout)
report = dict(stage=303, attempt=attempt, real_module_dlopen_contract_exit=q.returncode, aarch64_werror_compile=True,
              hardware_verified=False, synthetic_sensor_delay_frames=3, modeled_scene_steps=4,
              frames=int(model[1]) if model else 0, proposals=int(model[2]) if model else 0,
              suppressed_feedback_frames=int(model[3]) if model else 0,
              prior_manual_packet_and_error_contract_pass=b'IPA_CONTRACT_PASS' in q.stdout,
              ae_simulation_pass=model is not None and q.returncode == 0,
              module_sha256=hashlib.sha256((SDK / tree.lstrip('/') / 'output/src/ipa/camss-vfe/ipa_camss_vfe.so').read_bytes()).hexdigest(),
              test_source_sha256=hashlib.sha256((HERE / 'ipa-contract.cpp').read_bytes()).hexdigest())
(HERE / 'ipa-contract-validation.json').write_text(json.dumps(report, indent=2) + '\n')
assert q.returncode == 0
