"""Snapshot existing build-input receipts. No runtime entry, build or test is executed."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BUILD = REF / 'charging-oem-audit-20261023/phosh-private-build-inputs-501-r1'
ORIGINAL = REF / 'charging-ui-audit-20261023/phosh-rollback-original-501'
SOURCE = REF / 'charging-ui-audit-20261023/phosh-connection-source-r8'
CANDIDATE = REF / 'charging-ui-audit-20261023/phosh-external-power-candidate-r1'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
rollback, live = read(ORIGINAL / 'verified-result.json'), read(ORIGINAL / 'live-preflight-result.json')
assert rollback['three_runtime_splits_ready'] and rollback['schema_ready']
assert len(rollback['packages']) == 4 and all(p['signature_and_identity_passed'] for p in rollback['packages'])
assert live['passed'] and live['all_original_files'] and live['original_package_file_count'] == 72 and not live['mismatches']
recipe = (SOURCE / 'phosh-APKBUILD').read_text()
build_source = (BUILD / 'prepare-and-build-phosh.py').read_text()
for option in ['-Db_lto=true', '-Dphoc_tests=disabled', '-Dman=true', '-Dbindings-lib=true']:
    assert option in recipe and option in build_source
assert 'install_if="$pkgname=$pkgver-r$pkgrel xdg-desktop-portal>=1.17.1"' in recipe
assert 'candidate_pkgrel\':3001' in build_source
layer = read(BUILD / 'input-layer-result.json')
assert layer['terminal'] and layer['exact_original_payload_count'] == 304 and layer['extracted'] == 306
assert layer['different_C_same_source_private_tool_count'] == 2 and layer['original_and_private_db_world_unchanged']
feedback = read(BUILD / 'feedback-interfaces-result.json')
assert feedback['runtime_original_bytes_retained']
assert feedback['runtime_sha256_before'] == feedback['runtime_sha256_after']
assert feedback['temporary_built_library_not_used_for_phosh_link']
initial = read(BUILD / 'phosh-build-result.json')
assert initial['terminal'] and initial['returncode'] == 1
assert sha(BUILD / 'history-configure01/phosh-build-result.json') == sha(BUILD / 'phosh-build-result.json')
paths = [SOURCE / 'phosh-APKBUILD', CANDIDATE / 'source-result.json', CANDIDATE / 'external-power-marker.patch',
         BUILD / 'prepare-and-build-phosh.py', BUILD / 'generate-xkb-pc-and-resume.py',
         BUILD / 'input-layer-result.json', BUILD / 'three-inputs-result.json', BUILD / 'feedback-interfaces-result.json',
         BUILD / 'private-tools-links-result.json', BUILD / 'original-split-index.json', BUILD / 'phosh-build-result.json',
         ORIGINAL / 'verified-result.json', ORIGINAL / 'live-preflight-result.json']
result = {
    'status': 'pending_actual_build_and_packages', 'review_passed': False,
    'scope': 'preliminary recipe/input/rollback binding only, while actual resumed build is running',
    'files': {str(p.relative_to(REF)).replace('\\', '/'): sha(p) for p in paths},
    'reviewed_facts': ['original four r3 rollback payloads signed/index-matched; 72 original runtime files matched live preflight',
                       'pinned original0.57.0 recipe four Meson options and LTO retained in build script',
                       'independent candidate pkgrel3001 requested, not an actual packaged identity yet',
                       'original portalsconf install_if requires exact matching phosh version plus portal>=1.17.1',
                       '306 payload build layer explicitly distinguished from a complete package transaction and from phone payload',
                       'private generated feedback interfaces retain original runtime library bytes for linking',
                       'public initial configure failure retained; resumed build status must not be inferred from that old receipt'],
    'pending': ['actual resumed build terminal and compiler target/options',
                'four same-build runtime APK identity/content/control metadata and no development-input leakage',
                'candidate DT_NEEDED and actual dynamic exports versus installed runtime',
                'compiled GTK template/resource evidence; Xvfb subtree is not full TopPanel instantiation'],
    'private_active_log_access': 'Windows UNC denied; no WSL fallback, permission change or process action',
    'no_new_substantive_blocker_found_in_read_inputs': True,
    'old_ten_groups_or_full_device_suite_rerun': False,
    'device_SDK_build_shared_Git_used': False
}
(HERE / 'preliminary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'preliminary_sha256': sha(HERE / 'preliminary.json'), 'status': result['status']}))
