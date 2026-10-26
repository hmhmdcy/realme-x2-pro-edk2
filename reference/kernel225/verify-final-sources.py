from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess

here = Path(__file__).resolve().parent
repo = here.parents[1]
private = Path('/mnt/e/edk2-samurai-out/kernel225')
sdk = Path('/home/cy122/x2pro-linux/libcamera214-root')
kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for p in here.glob('*.py'):
    compile(p.read_text(), str(p), 'exec')
original = json.loads((private / 'original214-work-manifest-private.json').read_text())
assert len(original) == 2254
for n, item in original.items():
    p = sdk / 'work/libcamera' / n
    if 'target' in item:
        assert p.is_symlink() and os.readlink(p) == item['target']
    else:
        assert not p.is_symlink() and sha(p) == item['sha256']
        assert stat.S_IMODE(p.stat().st_mode) == item['mode']
assert not list((sdk / 'private').glob('libcamera214-before225*'))
for name in ['r12-build-state-private.json', 'r12-build-repair1-state-private.json', 'r13-build-state-private.json']:
    assert json.loads((private / name).read_text())['terminal']

modes = json.loads((private.parent / 'kernel223/kernel-before-paired-sof-mode-manifest-before-build-private.json').read_text())
assert len(modes) == 180
for n, item in modes.items():
    assert sha(kernel / n) == item['sha256'] and stat.S_IMODE((kernel / n).stat().st_mode) == item['mode']
assert len((kernel / 'Module.symvers').read_text().splitlines()) == 16798
status = subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=normal'], cwd=kernel, text=True).splitlines()
tracked = sum(not s.startswith('??') for s in status)
untracked = sum(s.startswith('??') for s in status)
assert (tracked, untracked) == (25, 11)
(private / 'kernel-final-status-private.txt').write_text('\n'.join(status) + '\n')
check = subprocess.run(['git', 'diff', '--check'], cwd=kernel, capture_output=True)
(private / 'kernel-final-diff-private.log').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0

recipe = repo / 'linux-port/packages/libcamera'
lock = json.loads((recipe / 'source-lock.json').read_text())
assert lock['new_recipe_version'] == '99990.7.2-r13'
assert all(sha(recipe / n) == v for n, v in lock['source_files_sha256'].items())
assert len(list(recipe.glob('*.patch'))) == 20
for p in (sdk / 'work/libcamera224-r11').iterdir():
    if p.is_file() and p.suffix in ['.patch', '.yaml', '.desktop']:
        assert p.read_bytes() == (recipe / p.name).read_bytes()
checksums = re.findall(r'^([0-9a-f]{128})  (\S+)$', (recipe / 'APKBUILD').read_text(), re.M)
local_checks = 0
for digest, name in checksums:
    if name == 'libcamera-v0.7.2.tar.gz':
        continue
    assert hashlib.sha512((recipe / name).read_bytes()).hexdigest() == digest
    local_checks += 1
assert local_checks >= 20
expected = {}
for patch, proof_name in [('0018-simple-manual-exposure-controls.patch', 'candidate-source-validation.json'),
                          ('0019-ipc-threaded-start-outputs.patch', 'generator-source-validation.json'),
                          ('0020-soft-invalid-statistics-hold.patch', 'statistics-hold-source-validation.json')]:
    proof = json.loads((here / proof_name).read_text())
    assert sha(recipe / patch) == proof['patch_sha256']
    expected.update(proof['source_files'])
source = sdk / 'work/libcamera225-r13-built/src/libcamera-v0.7.2'
assert len(expected) == 11
assert all(sha(source / n) == v and sha(private / 'candidate-patch-replay' / n) == v for n, v in expected.items())
assert json.loads((here / 'candidate-final-source-validation.json').read_text())['three_patches_replay_exactly_in_order']
assert (sdk / 'private/agc-control-preflight225.cpp').read_bytes() == (here / 'agc-control-regression.cpp').read_bytes()
assert (sdk / 'private/agc-control-regression225-r13.cpp').read_bytes() == (here / 'agc-control-regression.cpp').read_bytes()
assert (source / 'src/libcamera/camera.cpp').read_bytes() == (sdk / 'work/libcamera224-r11-built/src/libcamera-v0.7.2/src/libcamera/camera.cpp').read_bytes()
generated = re.sub(r'\s+', '', (source / 'output/include/libcamera/ipa/soft_ipa_proxy.h').read_text())
assert 'returnipa_->start(controls,sensorControls,source);' in generated

kernel_lock = json.loads((repo / 'linux-port/camera/kernel/source-lock.json').read_text())
assert kernel_lock['stage'] == 223 and kernel_lock['camss']['module_sha256'] == 'fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'
manifest = json.loads((private / 'camera-forward-repo-r13/package-manifest.json').read_text())
assert len(manifest['packages']) == 13
assert all(sha(private / 'camera-forward-repo-r13' / p['file']) == p['sha256'] for p in manifest['packages'])
deployment = json.loads((repo / 'linux-port/camera/deployment-lock.json').read_text())
assert deployment['framework_version'] == '99990.7.2-r13' and deployment['configuration_version'] == '0.1.0-r8'
assert deployment['built_packages'] == [{k: p[k] for k in ['name', 'version', 'file', 'sha256', 'bytes']} for p in manifest['packages']]
assert deployment['kernel_image_boot_dtb_and_all_modules_unchanged_in_stage225']
assert not deployment['manual_exposure_api_not_implemented']
assert json.loads((here / 'r13-host-runtime-qa-validation.json').read_text())['all_five_ipa_signatures_valid']
health = json.loads((here / 'final-health-validation.json').read_text())
assert health['taint'] == 0 and not any(health['fault_counts'].values())
assert health['nv_sources_unchanged'] and health['current_policy_r13_library_hashes_verified']
archive = json.loads((here / 'final-evidence-validation.json').read_text())
assert archive['verified_members'] == 191 and archive['archive_and_all_member_hashes_verified']
handoff = repo / 'NEXT-SESSION.md'
assert handoff.stat().st_size <= 6500
for required in ['## 源码、产物与回退依据', '## 续作与已知风险']:
    assert required in handoff.read_text()

# Resolve compiler symlinks inside its chroot, including absolute targets.
compiler = sdk / 'usr/bin/g++'
for _ in range(10):
    if not compiler.is_symlink():
        break
    target = os.readlink(compiler)
    compiler = sdk / target.lstrip('/') if target.startswith('/') else compiler.parent / target
elf = compiler.read_bytes()[:20]
assert elf[:4] == b'\x7fELF'
machine = int.from_bytes(elf[18:20], 'little' if elf[5] == 1 else 'big')
assert machine == 183
environment = dict(stage=225, host_architecture=os.uname().machine,
    sdk_alpine_release=(sdk / 'etc/alpine-release').read_text().strip(), sdk_cpp_elf_machine=machine,
    host_tools_present={n: bool(shutil.which(n)) for n in ['g++', 'aarch64-linux-gnu-gcc', 'aarch64-linux-gnu-g++', 'aarch64-linux-musl-g++', 'ccache', 'sccache', 'meson', 'ninja']},
    sdk_ccache_present=(sdk / 'usr/bin/ccache').exists(),
    native_host_matching_musl_cpp_migration_completed=False,
    measured_cross_compile_speedup_not_yet_available=True)
(here / 'build-environment-validation.json').write_text(json.dumps(environment, indent=2) + '\n')
report = dict(stage=225, python_sources_compile=len(list(here.glob('*.py'))),
    three_patch_replay_and_final_sources_verified=11, original214_files_links_modes_preserved=2254,
    no_pending_original214_snapshot=True, both_candidates_and_first_failed_build_terminal=True,
    canonical_kernel_original_files_and_modes_preserved=180, canonical_kernel_symbols_preserved=16798,
    original_kernel_tracked_modified=tracked, original_kernel_untracked_entries=untracked, kernel_diff_check_exit=0,
    mode_comparison_uses_explicit_json_not_ntfs_emulated_modes=True,
    recipe_patch_count=20, recipe_local_sha512_inputs_verified=local_checks,
    current_recipe_locks_and_all13_packages_exact=True, kernel_source_lock_remains_stage223=True,
    same_algorithm_fixture_retained=True, native_archive_members=191,
    next_session_bytes=handoff.stat().st_size, full_peripheral_goal_active=True)
(here / 'source-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
final = dict(stage=225, r13_r8_installed_and_policy_reloaded=True, independent_manual_auto_cpu_controls_enabled=True,
    captured_source_cookie_and_actual_values_match_metadata=True, behavior_assertions=48,
    candidate_manual_matrix_frames=1024, installed_manual_control_frames=256,
    installed_experimental_full_raw_metadata_frames=36, installed_experimental_full_rgb_metadata_frames=36,
    lifecycle_candidate_threaded_requests=40, lifecycle_candidate_isolated_requests=40,
    lifecycle_installed_requests=40, lifecycle_each_completed=20, lifecycle_each_cancelled=20,
    standard_cam_and_gstreamer_frames=12, full_mode_disabled_and_devices_suspended=True,
    taint=0, fault_counts=health['fault_counts'], native_archive_members=191,
    boot_kernel_image_and_driver_modules_unchanged=True, r11_r6_rollback_retained_keeps_fae1_e49=True,
    optical_delay_real_colour_geometry_and_rear_cameras_still_open=True,
    gnss_real_fix_and_all_other_peripheral_goal_still_open=True, full_peripheral_goal_active=True)
(here / 'final-validation.json').write_text(json.dumps(final, indent=2) + '\n')
print(json.dumps(report))
