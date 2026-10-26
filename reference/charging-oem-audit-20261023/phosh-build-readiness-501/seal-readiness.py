"""Bind cached read-only findings, without invoking a solver or build tool."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda b: hashlib.sha256(b).hexdigest()
load = lambda p: json.loads(p.read_bytes())
inventory = load(HERE/'inventory-result.json')
analysis = load(HERE/'cached-input-analysis.json')
actual_path = Path('E:/edk2-samurai-out/charging-management-20261023/latency-baseline-20261024-01-private/stdout-private.json')
actual = load(actual_path)
catalogue = [i for i in analysis['cached_index_contents_only_not_new_signature_verification']
             if 'aarch64' in i['architectures']]
community = next(i for i in catalogue if i['path'].endswith('/cache_apk_aarch64/APKINDEX.d022dfc8.tar.gz'))
matched = {}
for name in ['phosh','upower']:
    fields = actual['packages'][name]['fields']
    indexed = community['selected'][name]
    for key in ['V','A','c','D','p','C']:
        assert fields[key] == indexed[key], (name,key)
    matched[name] = {key:fields[key] for key in ['V','A','c','C']}

pins = {}
for name in inventory['seed']['missing_makedepends'] + ['xvfb-run','xmlstarlet']:
    choices = [(i, i['selected'][name]) for i in catalogue if name in i['selected']]
    versions = {p['V'] for i,p in choices}
    assert len(versions) == 1, name
    pins[name] = {'version':versions.pop(),
                  'index_sha256':sorted({i['sha256'] for i,p in choices}),
                  'package_checksum':sorted({p['C'] for i,p in choices})}
assert len(inventory['seed']['missing_makedepends']) == 24
assert not any(analysis['cached_missing_direct_makedepends'].values())

refs = [ROOT/'reference/kernel214/build-root-validation.json',
        ROOT/'reference/kernel214/create-build-root.py',
        ROOT/'reference/charging-ui-audit-20261023/phosh-connection-source-r8/phosh-APKBUILD',
        ROOT/'reference/charging-ui-audit-20261023/phosh-external-power-candidate-r1/delivery.json',
        ROOT/'reference/charging-ui-audit-20261023/phosh-external-power-candidate-r1/cache-inventory-result.json']
result = {
    'status':'private-aarch64-musl-build-path-feasible-dependency-solve-not-yet-performed',
    'new_build_or_package_install_performed':False,
    'new_network_or_dependency_download_performed':False,
    'target_or_SDK_tool_executed':False,
    'device_access_or_Git':False,
    'original_seed_db_and_world_unchanged':inventory['seed_db_and_world_unchanged'],
    'feasible_route': {
        'existing_qemu':inventory['host_tools']['qemu-aarch64'],
        'existing_binfmt':inventory['binfmt']['qemu-aarch64'],
        'private_copy_of_seed':inventory['seed']['path'],
        'cross_toolchain_or_qemu_download_required_for_selected_route':False,
        'reuse_existing_aarch64_gcc_abuild_meson_and_musl':True,
        'historical_same_seed_actual_emulated_compiler_success':True,
        'fresh_execution_in_new_copy_still_required':True,
    },
    'cached_index_matches_actual_installed_package_identity_and_dependency_string':matched,
    'private_runtime_metadata_sha256':sha(actual_path.read_bytes()),
    'cached_aarch64_community_index_sha256':community['sha256'],
    'missing_direct_makedepends':24,
    'missing_direct_makedepends_payloads_present_in_checked_caches':0,
    'pinned_direct_download_candidates_and_checkdepends':pins,
    'full_transitive_dependency_count_bytes_versions_and_signature_status':'not_solved_or_newly_verified; do not infer from direct count',
    'minimum_next_action':[
        'Create a new, non-hardlinked private seed copy; exclude original work/private signing material and never bind original writable directories. Override private abuild configuration, output/cache and private-root DB/world paths.',
        'Preserve/hash the old aarch64 main/community index bytes and verify their signatures with existing public Alpine keys. In the private copy only, use the existing native-host apk.static with a private repositories/cache file to simulate the pinned 24 development packages plus checkdepends and inspect its complete transaction.',
        'Fetch only missing files in that transaction from official repositories, verify against the frozen package/index identity and signatures; no unpinned edge upgrade or fallback. Refuse unavailable/mismatched historical packages and report the exact package.',
        'After the closure is private and verified, run the existing aarch64 toolchain through existing qemu/binfmt in the copy; apply fixed release prepare/Alpine splash patch plus external-power patch and original four Meson options, compile Phosh/package only.',
    ],
    'build_options':analysis['recipe']['required_explicit_options'],
    'additional_build_semantics':[
        'Original abuild-meson wrapper selects prefix/usr, plain, PIE, staticpic, wrap-mode=nodownload. Explicit recipe b_lto=true overrides wrapper b_lto=false.',
        'bindings-lib=true generates the Phosh GIR/typelib even though the introspection option defaults false: src/meson.build608-644. Include real g-ir-scanner/compiler through the solver dependency closure.',
        'Release tar contains gvc and libcall-ui. Do not fetch other Meson wrap projects; satisfy gmobile/libfeedback/libhandy with verified package dependencies.',
        'Original recipe defaults tests on and runs check under Xvfb; xvfb-run/xmlstarlet are not part of the 24 makedepends and remain required for matching check.',
    ],
    'limits':[
        'Cached package C/c/D matches do not reconstruct every installed runtime library/version: only the two package installed blocks were cached, not the full device APK database.',
        'The resulting candidate would be a source/version/options-matched aarch64-musl build, not a claim of bit-for-bit reconstruction of the original binary or proven target ABI until output dependencies/symbols are compared.',
        'No candidate package revision, signing, installation, desktop restart or rollback transaction was selected/executed in this read-only task.',
        'Positive LINE_POWER Online marker only; original Battery State/bolt/current/budget/charging policy remains unchanged.',
    ],
    'sources':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in refs},
    'local_evidence':{p.name:sha(p.read_bytes()) for p in [HERE/'inventory-result.json',HERE/'cached-input-analysis.json',HERE/'inventory-readonly.py',HERE/'analyze-cached-inputs.py']},
}
result['seal_program_sha256']=sha(Path(__file__).read_bytes())
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'result_sha256':sha((HERE/'result.json').read_bytes()),'same_package_identity':matched},indent=2))
