"""Bundle exact 441/468 candidates and current 440/434/363 rollback, without installing."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel475')
volume = storage.mount.mounted_build().parent
assert json.loads((HERE / 'package-r1-validation.json').read_bytes())['passed']
assert json.loads((HERE / 'source-recipe-validation.json').read_bytes())['passed']
target = PRIVATE / 'cohort-r1'
parser = argparse.ArgumentParser()
parser.add_argument('--resume-after-incomplete-symbol-audit', action='store_true')
args = parser.parse_args()
if args.resume_after_incomplete_symbol_audit:
    assert target.is_dir() and not (target / 'manifest-private.json').exists()
    assert sorted(path.relative_to(target).as_posix() for path in target.rglob('*') if path.is_file()) == sorted(
        kind + '/modules/' + name + '.ko' for kind in ['forward', 'rollback']
        for name in ['qcom_camss', 'qcom_camss_icp_a5_core', 'camss_icp_a5_m2m', 's5k3m5'])
    (PRIVATE / 'incomplete-original363-symbol-audit-failure-private.json').write_text(json.dumps(dict(
        stage=475, failed=True, phone_accessed=False, modules_loaded=False,
        phase='after copying exact four modules, before profiles/repositories',
        failed_assertion='camss_icp_a5_m2m imports missing from original363 symvers plus four candidate exports',
        missing_existing_provider_families=['v4l2_m2m_*', 'vb2_dma_sg_get_dmabuf_owner'],
        method_rejected_as_incomplete=True, retry_does_not_change_runtime_payload_or_provider_assumptions=True), indent=2) + '\n')
else:
    assert not target.exists()
    target.mkdir()
old = json.loads((PRIVATE.parent / 'kernel440/install-proof-r3-private.json').read_bytes())
release = '7.3.0-rc6-rmx1931-samurai-k363+'
new_build = json.loads((HERE.parent / 'kernel441/intree-build-validation.json').read_bytes())
old_build = json.loads((HERE.parent / 'kernel434/intree-build-validation.json').read_bytes())
assert new_build['passed'] and old_build['passed']
new_modules = {row['name'].replace('-', '_'): row for row in new_build['modules']}
old_modules = {row['name'].replace('-', '_'): row for row in old_build['modules']}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def note(source, kind, name):
    path = PRIVATE / f'{kind}-{name}.note'
    if args.resume_after_incomplete_symbol_audit:
        assert path.is_file()
        return sha(path)
    result = subprocess.run(['aarch64-linux-gnu-objcopy', '--dump-section', '.note.gnu.build-id=' + str(path), str(source)], capture_output=True)
    assert result.returncode == 0
    return sha(path)


def field(source, name):
    result = subprocess.run(['modinfo', '-F', name, str(source)], capture_output=True, text=True)
    assert result.returncode == 0
    return result.stdout.strip()


module_rows = []
for record in old['modules']:
    name = record['module']
    candidate = new_modules[name]
    prior = old_modules[name]
    new_path = Path(candidate['private_path'])
    old_path = Path(prior['private_path'])
    assert sha(new_path) == candidate['sha256']
    assert sha(old_path) == record['new_sha256'] == prior['sha256']
    module_rows.append(dict(name=name, path=record['path'], resolved_path=old['resolved_targets'][record['path']],
                            forward_source=new_path, rollback_source=old_path,
                            forward_sha256=candidate['sha256'], rollback_sha256=prior['sha256'],
                            expected_rollback_note=record['new_note_sha256']))
module_rows.append(dict(name='s5k3m5', path='/lib/modules/' + release + '/kernel/drivers/media/i2c/s5k3m5.ko',
                        resolved_path='/usr/lib/modules/' + release + '/kernel/drivers/media/i2c/s5k3m5.ko',
                        forward_source=PRIVATE.parent / 'kernel468/s5k3m5-mode2-build2.ko',
                        rollback_source=PRIVATE / 's5k3m5-formal363-rollback.ko',
                        forward_sha256='494910c99ef116b88038ac3dfcc020a90aa35bfcc610b6b37c152601ee758392',
                        rollback_sha256='966b29d8e05236ad3d123bdd60bf0202cc60886f60fc3186e06eda4df4059f29',
                        expected_rollback_note='1ad773945fe3f046e1ddb1b595430fe8c4135d38870dba86fd348763fe000814'))
manifest_modules = []
hardware = json.loads((HERE.parent / 'kernel474/hardware-validation.json').read_bytes())
assert hardware['passed'] and hardware['formal_restore_and_external_health_verified']
assert json.loads((HERE.parent / 'kernel468/module-build-validation.json').read_bytes())['passed']
for row in module_rows:
    for kind in ['forward', 'rollback']:
        source = row[kind + '_source']
        assert sha(source) == row[kind + '_sha256']
        assert field(source, 'vermagic') == release + ' SMP preempt mod_unload aarch64'
        assert field(source, 'intree') == 'Y'
        assert 'test_' not in field(source, 'parm')
        destination = target / kind / 'modules' / (row['name'] + '.ko')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert args.resume_after_incomplete_symbol_audit and sha(destination) == row[kind + '_sha256']
        else:
            shutil.copyfile(source, destination)
        row[kind + '_note_sha256'] = note(source, kind, row['name'])
        assert sha(destination) == row[kind + '_sha256']
    assert row['rollback_note_sha256'] == row['expected_rollback_note']
    manifest_modules.append({key: value for key, value in row.items() if not key.endswith('_source') and key != 'expected_rollback_note'})
profiles = []
for record in old['profiles']:
    model = record['model']
    prior = PRIVATE.parent / 'kernel440' / f'factory-{model}-private.yaml'
    forward = {'s5kgw1': PRIVATE.parent / 'kernel443/factory-s5kgw1-private.yaml',
               's5k3m5': PRIVATE.parent / 'kernel468/factory-s5k3m5-mode2-private.yaml'}.get(model, prior)
    assert sha(prior) == record['new_sha256']
    if model == 's5kgw1':
        assert sha(forward) == json.loads((HERE.parent / 'kernel443/profile-export-validation.json').read_bytes())['profile_sha256']
    if model == 's5k3m5':
        assert sha(forward) == '6396ced1039e352a14c7a07187e780596a3a4180b22391bca0b30f7518db4094'
    for kind, source in [('forward', forward), ('rollback', prior)]:
        destination = target / kind / 'profiles' / (model + '.yaml')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert sha(destination) == sha(source)
    profiles.append(dict(model=model, path=record['path'], resolved_path=old['resolved_targets'][record['path']],
                         forward_sha256=sha(forward), rollback_sha256=sha(prior),
                         forward_source_stage={'s5kgw1': 443, 's5k3m5': 468}.get(model, 440)))
for kind in ['forward', 'rollback']:
    shutil.copytree(PRIVATE / 'repository-r1' / kind, target / kind / 'repository')
    assert len(list((target / kind / 'repository').glob('*.apk'))) == 7
package_report = json.loads((HERE / 'package-r1-validation.json').read_bytes())
manifest = dict(stage=475, release=release, forward_packages={row['name']: row['version'] for row in package_report['packages']},
                rollback_packages=package_report['baseline_versions'], modules=manifest_modules, profiles=profiles,
                source_recipe_validation_sha256=sha(HERE / 'source-recipe-validation.json'),
                runtime_elf_byte_preserved=True, private_ipa_version=6, default_processed_output=[640, 480], raw_native_preserved=True,
                switch_order=['stop camera clients and PW/WP', 'prove no live camera FD and idle ownership',
                              'unload CAMSS before sensor unbind; unload m2m then core', 'replace sensor only with CAMSS absent',
                              'load sensor then matched core/m2m/CAMSS', 'install pinned seven-package cohort and private profiles',
                              'verify actual files, loaded notes, mappings and restart consumers'],
                rollback_order=['stop consumers; prove no live FD and idle', 'unload CAMSS, m2m/core before sensor unbind',
                                'restore original sensor then exact434 modules', 'restore exact440 r32/r27 packages and four profiles',
                                'restore repository/world metadata and consumer state from fresh transaction backup'],
                installed_on_phone=False, actual_device_transition_executed=False,
                module_abi_evidence=dict(exact_cached441_and468_build_inputs=True,
                    reused_actual474_load_and_restore_validation_sha256=sha(HERE.parent / 'kernel474/hardware-validation.json'),
                    only_original363_symbol_audit_incomplete=True, existing_provider_assumptions_not_changed=True),
                config_repository_world_service_backup_required_at_future_install=True)
files = {path.relative_to(target).as_posix(): sha(path) for path in sorted(target.rglob('*')) if path.is_file()}
manifest['files_sha256'] = files
(target / 'manifest-private.json').write_text(json.dumps(manifest, indent=2) + '\n')
archive = PRIVATE / 'cohort-r1-private.tar.gz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as stream:
    stream.add(target, arcname='cohort475', recursive=True)
report = dict(stage=475, signed_forward_packages=7, exact440_rollback_packages=7,
              modules=manifest_modules, profiles=profiles, original_sensor_rollback_from_verified363_archive=True,
              private_factory_data_in_apks=False, private_bundle_bytes=archive.stat().st_size, private_bundle_sha256=sha(archive),
              modules_loaded=False, phone_accessed=False, installed=False,
              isolated_root_module_profile_swap_validated=False, config_repository_world_restore_requires_fresh_device_backup=True,
              prior_incomplete_symbol_audit_failure_retained=True, abi_and_load_evidence_reused_from_exact441_468_and474=True,
              config_modversions_off_crc_not_additional_abi_proof=True, passed=True)
(HERE / 'private-payload-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(stage=475, complete_forward_and_current_formal_rollback=True, modules=4, private_profiles=4,
                      private_bundle_bytes=archive.stat().st_size, phone_accessed=False, passed=True)), flush=True)
