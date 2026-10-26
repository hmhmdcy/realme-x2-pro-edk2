"""Reuse the exact 473 source/build; patch only two core source files in a copy."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel489')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    volume = storage.mount.mounted_build().parent
    old = json.loads((HERE.parent / 'kernel473/source-state.json').read_bytes())
    baseline = Path(old['source'])
    new = storage.candidate()
    assert not new.exists() and not (HERE / 'source-state.json').exists()
    assert json.loads((HERE.parent / 'kernel487/source-validation.json').read_bytes())['passed']
    assert json.loads((HERE.parent / 'kernel488/validation.json').read_bytes())['passed']
    specifications = [
        ('kernel487', 'src/libcamera/sensor/camera_sensor_properties.cpp',
         '0001-camera-sensor-add-samurai-model-properties.patch', 'source-validation.json'),
        ('kernel488', 'src/libcamera/v4l2_subdevice.cpp',
         '0001-v4l2-recognize-uyyvyy10-0-5x30.patch', 'source-validation.json'),
    ]
    before = {row['path']: sha(baseline / row['path']) for row in old['source_hashes']}
    assert all(before[row['path']] == row['sha256'] for row in old['source_hashes'])
    runtime_paths = ['output/src/libcamera/libcamera.so.0.7.2',
                     'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
                     'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
                     'output/src/libcamera/proxy/worker/camss_ipa_proxy',
                     'output/src/libcamera/base/libcamera-base.so.0.7.2']
    runtime = {name: sha(baseline / name) for name in runtime_paths}
    assert runtime[runtime_paths[0]] == 'a21fcedde2f591f809a9c388a9a6ab78fa5072f33e06c91bbd55c8abf34cd97b'
    size = int(subprocess.check_output(['du', '-sb', str(baseline.parent.parent)]).split()[0])
    assert shutil.disk_usage(volume).free > size + 2 * 1024**3 + 256 * 1024**2
    PRIVATE.mkdir(exist_ok=True, parents=True)
    shutil.copytree(baseline.parent.parent, new, symlinks=True,
                    ignore=lambda directory, names: [name for name in names if name == '__pycache__' or name.startswith('pkg')])
    tree = new / 'src/libcamera-v0.7.2'
    changes = []
    for stage, relative, patch_name, receipt_name in specifications:
        proof = json.loads((HERE.parent / stage / receipt_name).read_bytes())
        baseline_sha = proof['baseline_source_sha256'] if stage == 'kernel487' else proof['baseline_sha256']
        candidate_sha = proof['candidate_source_sha256'] if stage == 'kernel487' else proof['candidate_sha256']
        assert sha(baseline / relative) == baseline_sha
        assert sha(tree / relative) == baseline_sha
        patch = HERE.parent / stage / patch_name
        assert sha(patch) == proof['patch_sha256']
        run = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(patch)],
                             cwd=tree, capture_output=True, timeout=15)
        (PRIVATE / (stage + '-patch.log')).write_bytes(run.stdout + run.stderr)
        assert run.returncode == 0 and b'offset' not in run.stdout.lower() and b'fuzz' not in run.stdout.lower()
        assert sha(tree / relative) == candidate_sha
        assert sha(baseline / relative) == baseline_sha
        changes.append({'path': relative, 'baseline_sha256': baseline_sha,
                        'candidate_sha256': candidate_sha, 'patch_sha256': sha(patch), 'stage': stage})
    assert before == {name: sha(baseline / name) for name in before}
    assert runtime == {name: sha(baseline / name) for name in runtime}
    assert runtime == {name: sha(tree / name) for name in runtime}
    assert shutil.disk_usage(volume).free > 2 * 1024**3 + 256 * 1024**2
    state = dict(stage=489, source=str(tree), baseline_source=str(baseline),
                 copied_build_tree_bytes=size, changes=changes, baseline_source_hashes=before,
                 runtime_before=runtime, original473_preserved=True, private_ipa_version=6,
                 build_pending=True, compiled=False, installed=False, phone_accessed=False,
                 sdk_used=False, ipa_coefficients_protocol_unchanged=True,
                 rotation_and_sensor_delay_not_adopted=True, passed=True)
    (HERE / 'source-state.json').write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps({'stage': 489, 'prepared': True, 'changed_files': [row['path'] for row in changes],
                      'copied_bytes': size, 'free_bytes': shutil.disk_usage(volume).free}, indent=2), flush=True)


if __name__ == '__main__':
    main()
