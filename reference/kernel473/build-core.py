"""Only the private 473 core target. Requires an explicit exclusive SDK handoff."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel473')
parser = argparse.ArgumentParser()
parser.add_argument('--attempt', required=True, choices=[f'r{x}' for x in range(1, 10)])
args = parser.parse_args()
attempt = args.attempt
volume = storage.mount.mounted_build().parent
tree = storage.candidate() / 'src/libcamera-v0.7.2'
baseline = volume / 'libcamera461-completion-ownership/src/libcamera-v0.7.2'
state = json.loads((HERE / 'source-state.json').read_bytes())
source_proof = json.loads((HERE / 'source-validation.json').read_bytes())
old_state = json.loads((HERE.parent / 'kernel461/source-state.json').read_bytes())
proof = json.loads((HERE.parent / 'kernel461/build-validation.json').read_bytes())
assert proof['passed'] and source_proof['passed'] and state['completion_ownership_fix']
assert state['processed_ipe_manager_capacity_lease'] and state['build_pending']
paths = {
    'libcamera.so.0.7.2': 'output/src/libcamera/libcamera.so.0.7.2',
    'ipa_camss_vfe.so': 'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
    'ipa_camss_vfe.so.sign': 'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
    'camss_ipa_proxy': 'output/src/libcamera/proxy/worker/camss_ipa_proxy',
}
expected = {row['name']: row['sha256'] for row in proof['runtime_files']}
assert expected['libcamera.so.0.7.2'] == '9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_sources():
    for row in state['source_hashes']:
        assert sha(tree / row['path']) == row['sha256'], row['path']
    for row in old_state['source_hashes']:
        assert sha(baseline / row['path']) == row['sha256'], row['path']
    for name, relative in paths.items():
        assert sha(baseline / relative) == expected[name], name


check_sources()
report_path = HERE / f'build-{attempt}-validation.json'
assert not report_path.exists() and not (HERE / 'build-validation.json').exists(), 'Never replay a terminal build attempt'
assert shutil.disk_usage(volume).free > 2 * 1024 ** 3 + 128 * 1024 ** 2
assert subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
for name, relative in paths.items():
    assert sha(tree / relative) == expected[name], 'Unexpected candidate output before core-only build: ' + name
version = tree / 'output/src/libcamera/version.cpp'
version_before = sha(version)
baseline_version_before = sha(baseline / 'output/src/libcamera/version.cpp')
target = ['ninja', '-C', '/work/libcamera/src/libcamera-v0.7.2/output', '-j2', 'src/libcamera/libcamera.so.0.7.2']
allowed = [
    'Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/pipeline_camss-vfe_camss_vfe.cpp.o',
    'Generating src/libcamera/version.cpp with a custom command',
    'Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/meson-generated_.._version.cpp.o',
    'Linking target src/libcamera/libcamera.so.0.7.2',
]
start = time.monotonic()
with storage.sdk_candidate():
    plan = subprocess.run(['chroot', str(storage.SDK), *target[:3], '-n', *target[3:]], capture_output=True)
    log = plan.stdout + plan.stderr
    (PRIVATE / f'core-plan-{attempt}-private.log').write_bytes(log)
    steps = [line for line in log.decode().splitlines() if re.match(r'^\[\d+/\d+\]', line)]
    assert plan.returncode == 0 and 2 <= len(steps) <= 4 and all(any(label in step for label in allowed) for step in steps), log.decode()
    assert any(allowed[0] in step for step in steps) and any(allowed[-1] in step for step in steps)
    print(json.dumps(dict(stage=473, attempt=attempt, build_started=True, planned_steps=steps)), flush=True)
    run = subprocess.run(['chroot', str(storage.SDK), *target], capture_output=True)
    (PRIVATE / f'core-build-{attempt}-private.log').write_bytes(run.stdout + run.stderr)
unmounted = subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
report = dict(stage=473, attempt=attempt, exit_code=run.returncode, seconds=round(time.monotonic() - start, 3),
              planned_steps=steps,
              executed_steps=[line for line in (run.stdout + run.stderr).decode().splitlines() if re.match(r'^\[\d+/\d+\]', line)],
              sdk_bind_unmounted=unmounted, requested_only_core_target=True, private_ipa_version=6,
              completion_ownership_fix_retained=True, processed_ipe_manager_capacity_lease=True,
              worker_affinity_explicitly_changed=False, drop_root_cause_fixed=False,
              phone_accessed=False, installed=False, hardware_validated=False, passed=False)
report_path.write_text(json.dumps(report, indent=2) + '\n')
assert run.returncode == 0 and unmounted, (run.stdout + run.stderr).decode()[-4000:]
check_sources()
assert sha(version) == version_before, 'Generated candidate version changed'
assert sha(baseline / 'output/src/libcamera/version.cpp') == baseline_version_before, '461 generated version changed'
files = []
for name, relative in paths.items():
    path = tree / relative
    digest = sha(path)
    if name == 'libcamera.so.0.7.2':
        assert digest != expected[name]
        shutil.copyfile(path, PRIVATE / name)
    else:
        assert digest == expected[name], name + ' unexpectedly changed'
    files.append(dict(name=name, bytes=path.stat().st_size, sha256=digest))
report.update(runtime_files=files, baseline461_preserved=True, ipa_proxy_signature_preserved=True,
              source_inputs_unchanged_during_build=True, generated_version_preserved=True, passed=True)
report_path.write_text(json.dumps(report, indent=2) + '\n')
(HERE / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state.update(build_pending=False, compiled=True)
(HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
