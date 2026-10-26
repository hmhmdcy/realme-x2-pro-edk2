"""Audit candidate provenance, source layering and pending hardware acceptance."""
from pathlib import Path
import difflib, hashlib, json, tarfile
import host
HERE = Path(__file__).resolve().parent
tree = Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build = json.loads((HERE / 'build-validation.json').read_text())
assert build['build_exit'] == 0
for name, digest in build['source_sha256'].items():
    assert hashlib.sha256((tree / name).read_bytes()).hexdigest() == digest
contract = json.loads((HERE / 'ipa-contract-validation.json').read_text())
assert contract['ae_simulation_pass']
assert hashlib.sha256((tree / 'output/src/ipa/camss-vfe/ipa_camss_vfe.so').read_bytes()).hexdigest() == contract['module_sha256']
baseline = {}
with tarfile.open(host.PRIVATE / 'tested302-source-private.tar.gz', 'r:gz') as tar:
    for item in tar.getmembers():
        if item.isfile(): baseline[item.name] = tar.extractfile(item).read().decode()
patch = []
for name in build['source_sha256']:
    before = baseline.get(name, '')
    after = (tree / name).read_text()
    if before != after:
        patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                    fromfile='a/' + name if before else '/dev/null', tofile='b/' + name))
(HERE / 'libcamera-hardware-ae.patch').write_text(''.join(patch))
shared = ['agc_mean_luminance.cpp', 'agc_mean_luminance.h', 'histogram.cpp', 'histogram.h',
          'exposure_mode_helper.cpp', 'exposure_mode_helper.h', 'camera_sensor_helper.cpp', 'camera_sensor_helper.h']
report = dict(stage=303, source_matches_build=True, tested302_source_and_bundle_preserved=True,
              direct_model_frames=contract['frames'], threaded_model_frames=720,
              phone_ssh_attempts=2, phone_reachable=False, hardware_experiments=0,
              phone_current_boot_not_reverified=True, last_verified_kernel_build=298,
              changed_layers=['libcamera hardware pipeline', 'hardware IPA', 'experimental per-mode tuning'],
              kernel_soc_driver_changed=False, sensor_driver_changed=False, board_dt_changed=False,
              product_packages_changed=False, calibration_partitions_written=False,
              isolated_ipc_pending=True, joint_sensor_latch_pending=True,
              hardware_ae_pending=True, awb_rgb_statistics_pending=True,
              multicamera_multimode_and_unit_calibration_pending=True,
              shared_libipa_source_sha256={n:hashlib.sha256((tree/'src/ipa/libipa'/n).read_bytes()).hexdigest() for n in shared},
              candidate_patch_sha256=hashlib.sha256((HERE/'libcamera-hardware-ae.patch').read_bytes()).hexdigest())
(HERE / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k!='shared_libipa_source_sha256'}, indent=2))
