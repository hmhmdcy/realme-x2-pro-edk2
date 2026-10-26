"""Check the completed deployment and keep acceptance limits explicit."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel296')
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checkpoint = load(HERE / 'checkpoint-validation.json')
for name, row in checkpoint['files'].items():
    p = ROOT / name
    assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256'], name
archive = ROOT / 'archive/camera-before296-2026-10-19'
manifest = load(archive / 'manifest.json')
assert manifest['prior_documented_stage'] == 295 and len(manifest['files']) == 9
for row in manifest['files']:
    p = archive / row['path']
    assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
deployment = load(ROOT / 'linux-port/camera/deployment-lock.json')
source = load(ROOT / 'linux-port/camera/kernel/source-lock.json')
identity = load(HERE / 'postboot-identity-validation.json')
health = load(HERE / 'final-health-validation.json')
package = load(HERE / 'boot-package-validation.json')
build = load(HERE / 'boot-candidate-build-validation.json')
assert all(d['stage'] == 296 for d in [deployment, source, identity, health, package, build])
assert deployment['kernel_source_commit'] == source['maintained_commit'] == package['commit'] == build['commit'] == checkpoint['source']
assert deployment['kernel_release'] == source['actual_kernel_release'] == identity['release'] == health['release'] == package['release'] == build['release']
assert deployment['kernel_modules'] == source['deployed_camera_modules'] == health['modules']
for key in ['image_sha256', 'logdump_sha256', 'dtb_sha256']:
    assert deployment[key] == package[key]
assert deployment['boot_sha256'] == package['firmware_boot_preserved_sha256']
assert deployment['kernel_config_sha256'] == build['artifacts']['.config']['sha256']
assert health['checked_runtime_healthy'] and not health['whole_system_healthy']
assert not health['first_statistics_packet_invalid'] and health['standard_bhist_initialization_verified']
assert not health['statistics_ready_for_automatic_exposure'] and not deployment['statistics_ready_for_automatic_exposure']
assert not deployment['ssc_boot_start_failed'] and deployment['system_services']['ssc_running']
assert not deployment['system_services']['temporary_nodeps_desktop_start']
for name in ['statistics-pixel-validation.json', 'statistics-r2-pixel-validation.json', 'four-camera-regression-validation.json']:
    assert load(HERE / name)['passed'], name
assert load(HERE / 'four-camera-regression-validation.json')['frames'] == 244
assert load(HERE / 'optical-statistics-validation.json')['all_packets_valid']
fix = load(HERE / 'startup-fix-validation.json')
assert fix['all_seven_startup_or_late_packets_valid'] and len(fix['startup_packets']) == 7
assert fix['hardware_image_frames'] == 216 and fix['hardware_statistics_packets'] == 198
assert fix['exact_image_stats_sof_association_not_proven'] and fix['ipa_blc_and_full_iq_incomplete']
assert not load(HERE.parent / 'kernel295/statistics-pixel-validation.json')['passed']
for tag in ['stats', 'optical', 'stats-late']:
    proof = load(HERE / (tag + '-tool-validation.json'))
    assert sha(PRIVATE / (tag + '-aarch64-private')) == proof['binary_sha256']
    assert sha(HERE / ('samurai-' + tag + '.c')) == proof['source_sha256']
compiled = 0
for p in HERE.glob('*.py'):
    compile(p.read_bytes(), str(p), 'exec')
    compiled += 1
text = (ROOT / 'NEXT-SESSION.md').read_text()
assert len(text.encode()) <= 6500 and '## 当前部署与启动身份' in text and '## 源码回退与下一步' in text
assert (ROOT / 'DOCS-INDEX.md').stat().st_size <= 10000
tree = '/home/cy122/x2pro-linux/camera279-isp-kernel'
git = lambda *a: subprocess.check_output(['git', '-C', tree, *a], text=True).strip()
assert git('rev-parse', 'HEAD') == checkpoint['source'] and not git('status', '--porcelain')
patch = subprocess.check_output(['git', '-C', tree, 'diff', '1aa1955077c977b611c722eca0bc467c3bf052ed..HEAD', '--', 'drivers/media/platform/qcom/camss'])
assert patch == (HERE / 'combined-stats-from293.patch').read_bytes()
assert sha(PRIVATE / 'Image-k296-private') == package['image_sha256']
assert sha(PRIVATE / 'logdump-k296-candidate-private.img') == package['logdump_sha256']
parent = load(HERE.parent / 'kernel295/boot-candidate-build-validation.json')
for name, row in parent['artifacts'].items():
    p = PRIVATE / 'completed-boot295' / Path(name).name
    assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
state = load(PRIVATE / 'boot-build-state-private.json')
assert state['terminal'] and state['exit_code'] == 0
report = dict(stage=296, current_source_and_runtime_receipts_consistent=True,
              source_clean=True, all_nine_archived_entrypoints_verified=True,
              source_and_binary_probe_hashes_verified=True, new_python_scripts_compiled=compiled,
              entrypoint_size_and_anchors_passed=True, previous_build_artifacts_verified=True,
              actual_default_ssc_success_preserved=True, prior_ssc_failure_not_claimed_fixed=True,
              first_statistics_initialization_fixed_in_tested_scope=True,
              parent_statistics_failure_preserved=True, statistics_not_ready_for_ipa=True,
              whole_system_healthy=False, complete_goal_still_active=True)
(HERE / 'final-checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
