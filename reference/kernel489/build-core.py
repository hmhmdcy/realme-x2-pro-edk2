"""Build only the two changed core objects after exclusive SDK handoff."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import time
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel489')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', required=True, choices=['r1', 'r2', 'r3'])
    args = parser.parse_args()
    volume = storage.mount.mounted_build().parent
    state = json.loads((HERE / 'source-state.json').read_bytes())
    assert state['build_pending'] and not state['compiled']
    tree, baseline = Path(state['source']), Path(state['baseline_source'])
    output = PRIVATE / ('build-' + args.attempt)
    assert not output.exists()
    output.mkdir()
    assert shutil.disk_usage(volume).free > 2 * 1024**3 + 128 * 1024**2
    for row in state['changes']:
        assert sha(tree / row['path']) == row['candidate_sha256']
        assert sha(baseline / row['path']) == row['baseline_sha256']
    for relative, digest in state['runtime_before'].items():
        assert sha(tree / relative) == sha(baseline / relative) == digest
    version = tree / 'output/src/libcamera/version.cpp'
    old_version = sha(version)
    allowed = [
        'Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/sensor_camera_sensor_properties.cpp.o',
        'Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/v4l2_subdevice.cpp.o',
        'Generating src/libcamera/version.cpp with a custom command',
        'Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/meson-generated_.._version.cpp.o',
        'Linking target src/libcamera/libcamera.so.0.7.2',
    ]
    target = ['ninja', '-C', '/work/libcamera/src/libcamera-v0.7.2/output', '-j2', 'src/libcamera/libcamera.so.0.7.2']
    start = time.monotonic()
    with storage.sdk_candidate():
        plan = subprocess.run(['chroot', str(storage.SDK), *target[:3], '-n', *target[3:]], capture_output=True, timeout=45)
        (output / 'plan.log').write_bytes(plan.stdout + plan.stderr)
        steps = [line for line in (plan.stdout + plan.stderr).decode().splitlines() if re.match(r'^\[\d+/\d+\]', line)]
        assert plan.returncode == 0 and 3 <= len(steps) <= 5 and all(any(text in step for text in allowed) for step in steps), (plan.stdout + plan.stderr).decode()
        assert all(any(text in step for step in steps) for text in (allowed[0], allowed[1], allowed[-1]))
        print(json.dumps({'stage': 489, 'planned_steps': steps}), flush=True)
        run = subprocess.run(['chroot', str(storage.SDK), *target], capture_output=True, timeout=300)
        (output / 'build.log').write_bytes(run.stdout + run.stderr)
    unbound = subprocess.run(['mountpoint', '-q', str(storage.SDK / 'work/libcamera')], capture_output=True).returncode != 0
    report = dict(stage=489, attempt=args.attempt, passed=False, exit_code=run.returncode,
                  seconds=round(time.monotonic() - start, 3), planned_steps=steps,
                  executed_steps=[line for line in (run.stdout + run.stderr).decode().splitlines() if re.match(r'^\[\d+/\d+\]', line)],
                  sdk_bind_unmounted=unbound, phone_accessed=False, installed=False,
                  only_core_target_requested=True, private_ipa_version=6)
    receipt = HERE / ('build-' + args.attempt + '-validation.json')
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    assert run.returncode == 0 and unbound, (run.stdout + run.stderr).decode()[-4000:]
    assert sha(version) == old_version
    for row in state['changes']:
        assert sha(tree / row['path']) == row['candidate_sha256']
        assert sha(baseline / row['path']) == row['baseline_sha256']
    for relative, digest in state['runtime_before'].items():
        assert sha(baseline / relative) == digest
        if relative != 'output/src/libcamera/libcamera.so.0.7.2':
            assert sha(tree / relative) == digest
    for relative, digest in state['baseline_source_hashes'].items():
        assert sha(baseline / relative) == digest
        assert sha(tree / relative) == digest
    raw_core = output / 'libcamera-build.so.0.7.2'
    shutil.copyfile(tree / 'output/src/libcamera/libcamera.so.0.7.2', raw_core)
    spec = importlib.util.spec_from_file_location('normalizer489', HERE.parent / 'kernel485/normalize-core.py')
    normalizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(normalizer)
    delta = normalizer.normalize(raw_core, output / 'libcamera.so.0.7.2', sha(raw_core), b'$ORIGIN/base:/')
    report.update(passed=True, original473_preserved=True, ipa_proxy_base_signature_preserved=True,
                  generated_version_preserved=True, normalized_core=delta,
                  ipa_coefficients_protocol_unchanged=True, arm64_executed=False, hardware_validated=False)
    receipt.write_text(json.dumps(report, indent=2) + '\n')
    (HERE / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    state.update(build_pending=False, compiled=True, sdk_used=True)
    (HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
