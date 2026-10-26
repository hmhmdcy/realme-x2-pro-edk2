"""Audit cached acceptance and export current ordinary-5V delivery, offline only.
Run as WSL root for the storage helper. No phone connection or shared mutation.
Historical phase receipts remain intact; delivery.json describes the final state.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
assert os.geteuid() == 0, 'Use WSL root with the existing storage lock'
sys.path.insert(0, str(ref.parent / 'kernel284'))
import storage
shared = storage.mounted_build()

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def read(name):
    return json.loads((ref / name).read_text())

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

baseline = read('baseline.json')
assert shared == Path(baseline['build'])
checked = {p: sha(p) == expected for p, expected in baseline['files'].items()}
assert len(checked) == 7 and all(checked.values()), checked
head = subprocess.check_output(['git', '-C', baseline['source'], 'rev-parse', 'HEAD'], text=True).strip()
assert head == baseline['head'], head

tests = read('test-result.json')
protocol = read('protocol-test-result.json')
rollback = read('rollback-test-result.json')
assert tests['passed'] and protocol['passed'] and rollback['passed']
transport = read('gauge-transport-test-result.json')
observer_tests = read('health-observer-test-result.json')
for receipt in [transport, observer_tests]:
    assert receipt['passed']
    for name, expected in receipt['tested_files'].items():
        assert sha(ref / name) == expected, name
assert transport['real_fixture_sha256'] == protocol['real_fixture_sha256']
for name, key in [('mp2650-core.h', 'tested_core_sha256'), ('oem-profile.h', 'tested_profile_sha256'),
                  ('test-core.c', 'harness_sha256')]:
    assert sha(ref / name) == tests[key], name
for name, expected in protocol['tested_files'].items():
    assert sha(ref / name) == expected, name
assert sha(ref / 'control-trial.py') == rollback['source_sha256']

build = read('integrated-build-result.json')
assert build['configuration_differences'] == {}
source_view = Path(build['source_view']) / 'drivers/power/supply'
for name, expected in build['sources'].items():
    assert sha(ref / name) == expected == sha(source_view / name), name
log = Path(build['private_build']).parent / 'integrated-build.log'
assert not re.search(r'warning:|error:|undefined!', log.read_text(), re.I)
out.mkdir(parents=True, exist_ok=True)
modules = {}
for name, entry in build['modules'].items():
    path = Path(entry['path'])
    assert sha(path) == entry['sha256'], name
    header = subprocess.check_output(['aarch64-linux-gnu-readelf', '-h', str(path)], text=True)
    assert re.search(r'Machine:\s+AArch64', header)
    vermagic = subprocess.check_output(['modinfo', '-F', 'vermagic', str(path)], text=True).strip()
    assert vermagic.startswith(baseline['release'] + ' ')
    assert subprocess.check_output(['modinfo', '-F', 'intree', str(path)], text=True).strip() == 'Y'
    target = name + '.ko'
    shutil.copy2(path, out / target)
    modules[target] = {'sha256': sha(path), 'bytes': path.stat().st_size,
                       'vermagic': vermagic, 'intree': True}
assert len(modules) == 3

payload = out / 'service/samurai-charging-payload.tar.gz'
manifest_path = out / 'service/manifest.json'
payload_build = read('service-payload-result.json')
manifest = json.loads(manifest_path.read_text())
update = read('pm-link-update-result.json')
assert update['passed'] and update['taint'] == 0 and update['usb_provider_unloaded'] is False
assert sha(payload) == payload_build['payload_sha256']
assert sha(manifest_path) == payload_build['manifest_sha256'] == update['new_manifest_sha256']
assert manifest['installed_files'] == payload_build['files']
assert manifest['release'] == baseline['release']
assert manifest['default_input_cap_ua'] == 900000 and manifest['default_charge_cap_ua'] == 250000
service_sources = {
    '/usr/sbin/samurai-charging': ref / 'samurai-charging.py',
    '/etc/init.d/samurai-charging': ref / 'samurai-charging.openrc',
    '/usr/lib/samurai-charging/control-trial.py': ref / 'control-trial.py',
    '/usr/lib/samurai-charging/live-session.py': ref / 'live-session.py',
}
for name, path in service_sources.items():
    assert sha(path) == manifest['installed_files'][name], name
for name, entry in manifest['modules'].items():
    assert entry['sha256'] == modules[name + '.ko']['sha256']
    assert manifest['installed_files'][entry['target']] == entry['sha256']
expected_payload = dict(manifest['installed_files'])
expected_payload['/usr/share/samurai-charging/manifest.json'] = sha(manifest_path)
with tarfile.open(payload) as archive:
    members = archive.getmembers()
    assert {'/' + m.name for m in members} == expected_payload.keys() and len(members) == 8
    for member in members:
        name = '/' + member.name
        assert member.isfile() and member.uid == member.gid == 0
        mode = 0o755 if name.startswith(('/usr/sbin/', '/etc/init.d/')) else 0o600
        assert member.mode == mode, name
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == expected_payload[name]
subprocess.run(['sh', '-n', str(ref / 'samurai-charging.openrc')], check=True)

accepted_names = ['recovery-result.json', 'shadow-result.json', 'control-trial-result.json',
                  'service-test-result.json', 'managed-boot-result.json',
                  'postboot-camera-result.json', 'pm-link-update-result.json', 'charging-pm-result.json',
                  'health-observation-result.json']
accepted = {name: read(name) for name in accepted_names}
for name, receipt in accepted.items():
    assert receipt['passed'] and receipt['taint'] == 0, name
pm = accepted['charging-pm-result.json']
health = accepted['health-observation-result.json']
assert health['audit_tool_sha256'] == observer_tests['tested_files']['charging-health.py']
assert health['acceptance_functions_unchanged'] and health['re_audited_without_new_device_access']
observer_evidence = [out / 'health-continued/charging-health-r1.py',
                     out / 'health-continued/health-observer-r1-test-result.json']
assert sha(observer_evidence[0]) == health['observer_sha256']
assert health['manifest_sha256'] == update['new_manifest_sha256']
assert health['configuration_or_service_writes'] == 0
for key in ['same_boot', 'rtc_s2idle_residency_proved', 'supplier_pm_order_verified',
            'charger_stop_and_fresh_resume_passed', 'charger_configuration_preserved',
            'boottime_session_retains_sleep', 'camera_and_four_services_unchanged']:
    assert pm[key], key
assert pm['trace_audit_pending'] is False
assert pm['suspend_stats_delta']['success'] == 1 and pm['suspend_stats_delta']['fail'] == 0
assert pm['rtc_irq_delta'] == 1 and pm['residency_seconds'] >= 14
assert pm['native_allowance_after']['ua'] == 100000 and not any(pm['fault_delta'].values())
managed = accepted['managed-boot-result.json']
assert managed['boot_readback_exact'] and managed['service_boot_enabled']
assert managed['kernel_modules_loaded_and_exact']
assert managed['actual_input_limit_ua'] == 900000 and managed['actual_charge_current_ua'] == 250000
assert managed['actual_pack_target_uv'] == 8725000

firmware = read('usb-boot-result.json')
flash = read('usb-flash-result.json')
assert flash['boot_flash_success'] and flash['partitions_flashed'] == ['boot']
assert firmware['firmware_only_dtb_changed'] and firmware['all_firmware_code_and_non_version_data_unchanged']
assert firmware['repository_dtb_restored']
assert firmware['boot_sha256'] == flash['boot_sha256'] == managed['boot_sha256']
artifacts = {
    'boot': (out / 'usb-boot/boot-charging-usb-dt.img', firmware['boot_sha256']),
    'rollback_boot': (out.parent / 'kernel389/boot-partition-k389-icp-platform.img', firmware['rollback_boot_sha256']),
    'dtb': (out / 'usb-dt/samurai-charging-usb-private.dtb', firmware['dtb_sha256']),
}
for name, (path, expected) in artifacts.items():
    assert sha(path) == expected, name
integration = read('kernel-integration-result.json')
assert sha(ref / 'kernel-integration.patch') == integration['patch_sha256']
patch_check = subprocess.run(['git', '-C', baseline['source'], 'apply', '--check', str(ref / 'kernel-integration.patch')],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
assert patch_check.returncode == 0, patch_check.stdout
integration['apply_check_passed'] = True
integration['apply_check_source_head'] = head
write(ref / 'kernel-integration-result.json', integration)

syntax_counts = {'python': 0, 'json': 0}
for path in ref.glob('*.py'):
    ast.parse(path.read_text(), filename=str(path))
    syntax_counts['python'] += 1
for path in ref.glob('*.json'):
    json.loads(path.read_text())
    syntax_counts['json'] += 1
links = []
for path in ref.glob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        link = link.strip('<>')
        if '://' in link or link.startswith('#'):
            continue
        target = path.parent / link.split('#')[0]
        assert target.is_file(), (path.name, link)
        links.append([path.name, link])

report = {
    'date': '2026-10-23', 'kind': 'deployed-ordinary-5v-charging-v3',
    'validation_revision': 4,
    'scope': 'OEM-profile protection, verified factory-cell queries, native USB input budget, ordinary charging and RTC s2idle recovery',
    'release': baseline['release'], 'modules': modules,
    'service_manifest_sha256': sha(manifest_path), 'service_payload_sha256': sha(payload),
    'payload_matches_installed_manifest_receipt': True, 'payload_repack_was_offline': True,
    'phone_accessed_during_work': True, 'flashed_during_work': True,
    'phone_accessed_by_finalizer': False, 'flashed_by_finalizer': False,
    'partitions_flashed': ['boot'], 'ordinary_5v_deployed': True,
    'defaults_ua': {'input_cap': 900000, 'charge_cap': 250000},
    'inherited_max_pack_target_uv': 8725000,
    'current_connection': {'type': 'CDP', 'source_allowance_ua': 1500000, 'native_configured_udc_ua': 100000},
    'pm': {'residency_seconds': pm['residency_seconds'], 'success_delta': 1, 'failure_delta': 0,
           'rtc_irq_delta': 1, 'taint': 0, 'supplier_order_and_fresh_resume_passed': True,
           'camera_and_four_services_unchanged': True},
    'tested_cases': {'policy': tests['policy_cases'], 'transactions': tests['transaction_cases'],
                     'source_latch_sequences': tests['source_latch_sequence_cases'],
                     'protocol_protection': protocol['protocol_protection_cases'],
                     'usb_budget': protocol['usb_budget_cases'], 'rollback': rollback['cases'],
                     'gauge_transport': transport['transport_cases'], 'health_observer': observer_tests['cases']},
    'read_only_health_observation': {'duration_seconds': health['duration_seconds'],
                                     'samples': health['sample_count'],
                                     'passed': health['passed'], 'configuration_or_service_writes': 0,
                                     'hardware_full_status_observed': health['hardware_full_status_observed'],
                                     'optional_battery_properties_captured': False,
                                     'executed_observer_files': {p.name: sha(p) for p in observer_evidence}},
    'validation_receipts': {name: sha(ref / name) for name in accepted_names},
    'historical_receipt_scope': {
        'control-trial-result.json': 'Earlier module hashes; not a new 300mA trial of v3',
        'service-test-result.json': 'V2 start/stop/restart/exact rollback; later v3 update and suspend have separate receipts',
        'usb-dt-result.json': 'Offline preparation before later flash',
        'usb-boot-result.json': 'Construction before deployment',
        'usb-flash-result.json': 'Flash before exact readback in managed-boot-result.json',
        'service-payload-result.json': 'Offline repack of installed file set; repack itself does not install or retest'},
    'incident_history': ['shadow-incident-result.json', 'recovery-result.json', 'shadow-result.json'],
    'deferred_by_user': ['Physical SDP port change and cable unplug/reconnect; retained current connection and prioritized standby recovery'],
    'not_accepted': ['SuperVOOC/PD fast charging', 'All physical temperature boundaries',
                     'Low-battery precharge, full termination and recharge', 'Long-duration endurance',
                     'Session accumulation across reboot', 'Independent stop on CPU-hang or permanent I2C failure',
                     'Permanent-failure enablement (inherited PF_EN remains 0)'],
    'coordination': {'phone_and_sdk_handed_back_to_camera449': True,
                     'native_usb_provider_must_remain_loaded_until_next_boot': True},
    'shared_baseline_files_unchanged': checked,
    'source_head_at_start': baseline['head'], 'source_head_at_finish': head,
    'kernel_patch_apply_check_passed': True, 'kernel_patch_applied': False,
    'syntax_checks': syntax_counts, 'local_document_links_checked': len(links),
    'large_artifacts_referenced_without_duplication': {
        name: {'path': str(path), 'sha256': expected, 'bytes': path.stat().st_size}
        for name, (path, expected) in artifacts.items()},
    'files': {p.name: sha(p) for p in sorted(ref.iterdir()) if p.is_file() and p.name != 'delivery.json'},
}
write(ref / 'delivery.json', report)
bundle = out / 'charging-management-20261023.tar.gz'
with tarfile.open(bundle, 'w:gz') as archive:
    for path in sorted(ref.iterdir()):
        if path.is_file():
            archive.add(path, arcname='charging-management-20261023/' + path.name)
    for name in modules:
        archive.add(out / name, arcname='charging-management-20261023/modules/' + name)
    for path in [payload, manifest_path]:
        archive.add(path, arcname='charging-management-20261023/service/' + path.name)
    for path in observer_evidence:
        archive.add(path, arcname='charging-management-20261023/evidence/' + path.name)
with tarfile.open(bundle) as archive:
    for member in archive.getmembers():
        assert member.isfile() and member.name.startswith('charging-management-20261023/')
        path = member.name.removeprefix('charging-management-20261023/')
        if path.startswith('evidence/'):
            original = out / 'health-continued' / path.removeprefix('evidence/')
        elif path.startswith(('modules/', 'service/')):
            original = out / (path.removeprefix('modules/') if path.startswith('modules/') else path)
        else:
            original = ref / path
        assert hashlib.sha256(archive.extractfile(member).read()).hexdigest() == sha(original), path
checksum_files = [*(out / name for name in modules), payload, manifest_path, bundle]
(out / 'SHA256SUMS').write_text(''.join(sha(path) + '  ' + str(path.relative_to(out)) + '\n' for path in checksum_files))
print(json.dumps({'kind': report['kind'], 'modules': modules, 'manifest_sha256': report['service_manifest_sha256'],
                  'shared_baseline_unchanged': all(checked.values()), 'kernel_patch_apply_check_passed': True,
                  'syntax_checks': syntax_counts, 'document_links': len(links), 'bundle': str(bundle),
                  'bytes': bundle.stat().st_size, 'bundle_sha256': sha(bundle), 'phone_accessed_by_finalizer': False}, indent=2))
