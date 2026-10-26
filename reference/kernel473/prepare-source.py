"""Copy the exact 461 core source/output, then apply only the processed-IPE gate."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel473')
PRIVATE.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument('--measure-only', action='store_true')
args = parser.parse_args()
volume = storage.mount.mounted_build().parent
baseline = volume / 'libcamera461-completion-ownership'
new = storage.candidate()
base_tree = baseline / 'src/libcamera-v0.7.2'
relative = 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
baseline_sha = 'befec1da3743545652adc669cc649860d6840738e38a3798305d213b2e874b40'
core_sha = '9b352a12a8825935155106d17b81bb33ac60c4d14d7d2007efaad9e3f06af3af'
helper_sha = '5801d89dcd326873df9d518df5a2667e5deeacf87bd0274bd1a241569bc9a463'
state = json.loads((HERE.parent / 'kernel461/source-state.json').read_bytes())
build = json.loads((HERE.parent / 'kernel461/build-validation.json').read_bytes())
assert build['passed'] and state['completion_ownership_fix'] and not state['build_pending']
paths = {
    'libcamera.so.0.7.2': 'output/src/libcamera/libcamera.so.0.7.2',
    'ipa_camss_vfe.so': 'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
    'ipa_camss_vfe.so.sign': 'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
    'camss_ipa_proxy': 'output/src/libcamera/proxy/worker/camss_ipa_proxy',
}
expected = {row['name']: row['sha256'] for row in build['runtime_files']}
assert expected['libcamera.so.0.7.2'] == core_sha


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def check_baseline():
    assert sha(base_tree / relative) == baseline_sha
    assert sha(base_tree / 'src/libcamera/pipeline/camss-vfe/thread_capacity.h') == helper_sha
    for row in state['source_hashes']:
        assert sha(base_tree / row['path']) == row['sha256'], row['path']
    for name, path in paths.items():
        assert sha(base_tree / path) == expected[name], name


def ignored(directory, names):
    return [name for name in names if name.startswith('pkg') or name == '__pycache__']


def inventory(root):
    rows = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(set(dirs) - set(ignored(directory, dirs)))
        for name in sorted(set(files) - set(ignored(directory, files))):
            path = Path(directory) / name
            key = path.relative_to(root).as_posix()
            rows[key] = {'symlink': os.readlink(path)} if path.is_symlink() else {'bytes': path.stat().st_size, 'sha256': sha(path)}
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                rows[path.relative_to(root).as_posix()] = {'symlink': os.readlink(path)}
    return rows


check_baseline()
before = inventory(baseline)
usage = sum(row.get('bytes', 0) for row in before.values())
free = shutil.disk_usage(volume).free
reserve = 2 * 1024 ** 3
headroom = 256 * 1024 ** 2
measurement = dict(stage=473, baseline_tree_bytes=usage, copied_entries=len(before), free_before_bytes=free,
                   required_reserve_bytes=reserve, extra_build_headroom_bytes=headroom,
                   fits_with_reserve=free > usage + reserve + headroom,
                   sdk_bound=False, phone_accessed=False)
(PRIVATE / 'source-size-private.json').write_text(json.dumps(measurement, indent=2) + '\n')
print(json.dumps(measurement), flush=True)
assert measurement['fits_with_reserve'], (free, usage)
if args.measure_only:
    raise SystemExit(0)
assert not new.exists(), 'Keep any partial candidate; do not overwrite/replay it'
assert not (HERE / 'source-validation.json').exists(), 'Source preparation is already terminal'
patch = HERE / '0001-camss-lease-manager-capacity-for-processed-ipe.patch'
base_bytes = (base_tree / relative).read_bytes()
old_gate = b'  if(d->lensActive_){\n   const auto capacity=d->focusCapacity_.acquire();'
new_gate = (b'  /* The Manager also runs FULL ownership, IPE dispatch and synchronous IPA\n'
            b'   * calls without a lens. Existing isolated workers are not retargeted by\n'
            b'   * this thread lease; retain its established start/stop lifetime. */\n'
            b'  if(d->lensActive_ || (d->processedEnabled_ && d->ipe_)){\n'
            b'   const auto capacity=d->focusCapacity_.acquire();')
assert base_bytes.count(old_gate) == 1
candidate_bytes = base_bytes.replace(old_gate, new_gate)
shutil.copytree(baseline, new, symlinks=True, ignore=ignored)
tree = new / 'src/libcamera-v0.7.2'
assert inventory(new) == before, 'Private copy differs before the patch'
for action, extra in [('dry-run', ['--dry-run']), ('apply', [])]:
    run = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(patch), *extra], cwd=tree, capture_output=True)
    log = run.stdout + run.stderr
    (PRIVATE / f'patch-{action}-private.log').write_bytes(log)
    assert run.returncode == 0 and b'offset' not in log.lower() and b'fuzz' not in log.lower(), log.decode()
assert (tree / relative).read_bytes() == candidate_bytes
after = inventory(new)
changed = [name for name in before if before[name] != after.get(name)]
assert changed == ['src/libcamera-v0.7.2/' + relative] and before.keys() == after.keys(), changed
assert inventory(baseline) == before, '461 baseline changed during the copy'
for name, path in paths.items():
    assert sha(tree / path) == expected[name], name
assert sha(tree / 'src/libcamera/pipeline/camss-vfe/thread_capacity.h') == helper_sha
assert shutil.disk_usage(volume).free > reserve + headroom
for row in state['source_hashes']:
    row['sha256'] = sha(tree / row['path'])
state.pop('successful_build', None)
state.update(stage=473, source=str(tree), baseline_stage=461, source_baseline_stage=461,
             changed_this_stage=[relative], completion_ownership_fix=True, processed_ipe_manager_capacity_lease=True,
             capacity_helper_unchanged=True, worker_affinity_explicitly_changed=False,
             build_pending=True, compiled=False, hardware_validated=False, installed=False)
(HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')
report = dict(measurement, free_after_bytes=shutil.disk_usage(volume).free,
              candidate_source_sha256=sha(tree / relative), baseline_source_sha256=baseline_sha,
              baseline_core_sha256=core_sha, capacity_helper_sha256=helper_sha, patch_sha256=sha(patch),
              only_one_source_changed=True, zero_fuzz_zero_offset=True, independent_output_copy=True,
              original461_preserved=True, ipa_proxy_signature_preserved=True, completion_ownership_fix_retained=True,
              built=False, hardware_validated=False, installed=False, passed=True)
(HERE / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
(PRIVATE / 'camss_vfe-candidate.cpp').write_bytes(candidate_bytes)
(PRIVATE / 'copy-inventory-private.json').write_text(json.dumps(before, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)

