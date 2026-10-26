"""Scope closure to the actual r15 transaction, preserving strict RGB failures."""
from pathlib import Path

R = Path(__file__).resolve().parent
source = (R.parent / 'kernel238/final-health.py').read_text()


def replace(old, new):
    global source
    assert source.count(old) == 1, old[:100]
    source = source.replace(old, new)


replace('"""Current238 scoped health; RGB startup black-frame failure is retained."""',
        '"""Current239 r15 default runtime health; optical acceptance stays open."""')
replace('import struct\n', 'import struct\nimport stat\n')
replace("out = root / 'k238-final-health'", "out = root / 'k239-final-health'")
start = source.index("contexts = ['k238-controlled")
end = source.index("\ntree = Path('/usr/lib/modules')", start)
source = source[:start] + '''contexts = ['k239-fixed-rgb-r14', 'k239-paired-r14', 'k239-r15-startup',
            'k239-front-r15-raw', 'k239-front-r15-rgb',
            'k239-r15-installed-startup', 'k239-odm-source']
for name in contexts:
    assert json.loads((root / name / 'state-private.json').read_text())['state'] == 'terminal', name
for name in contexts[:-1]:
    report = json.loads((root / name / 'summary.json').read_text())
    assert report['program_exit'] == 0 and not report['worker_exception']
    assert all(report[k] for k in ['all_formats_restored', 'media_graph_restored',
        'sensor_controls_restored', 'rails_unchanged', 'camera_devices_suspended', 'mclk1_mclk2_disabled'])
    assert not report['restore_errors'] and not any(report['fault_delta'].values())
    if 'front' in name:
        assert report['passed'] and len(report['frames']) == 6
    else:
        assert report['diagnostic_capture_completed'] and report['trace_instance_removed']
installed = json.loads((root / 'k239-r15-installed-startup/summary.json').read_text())
assert installed['default_environment_without_candidate_overrides']
assert installed['same_camera_two_start_stop_runs'] and installed['run_count'] == 2
assert len(installed['frames']) == 24 and not installed['strict_nonzero_frames_passed']
assert not installed['passed']  # Retain the independent strict all-nonzero failure.
odm = json.loads((root / 'k239-odm-source/summary.json').read_text())
assert odm['unmounted'] and odm['odm_before_after_equal'] and odm['no_gnss_set_or_search']
transaction = root / 'k239-r15-package-transaction'
assert json.loads((transaction / 'transaction-state-private.json').read_text())['state'] == 'verified'
assert json.loads((transaction / 'policy-reload-state-private.json').read_text())['state'] == 'verified'
policy = json.loads((transaction / 'policy-reload-summary.json').read_text())
assert all(policy[k] for k in ['new_r15_camera_libraries_loaded', 'no_old_deleted_camera_library_mappings',
    'no_candidate_path_environment_overrides', 'pipewire_and_all_desktop_process_identities_unchanged',
    'bluetooth_connected_devices_unchanged', 'no_pair_connect_or_disconnect_requested'])
assert not any('k239' in line for line in Path('/proc/self/mountinfo').read_text().splitlines())
assert not any(p.name.startswith('k239') for p in Path('/sys/kernel/tracing/instances').iterdir())

''' + source[end:]
old = """checked(['sha256sum', '-c', str(root / 'k236-baseline/userspace-check.sha256')], 'userspace')
checked(['sha256sum', '-c', str(root / 'k235-module-stage/loader-config-after.sha256')], 'loader-config')
assert Path('/lib/apk/db/installed').read_bytes() == (root / 'k236-baseline/installed-before-private.txt').read_bytes()
"""
new = '''manifest = json.loads((root / 'k239-r15-package-candidates/forward-manifest.json').read_text())
names = {p['name'] for p in manifest['packages']}
assert len(names) == 7
expected = {}
for package in manifest['packages']:
    for relative, item in package['files'].items():
        assert relative not in expected
        expected[relative] = item
        path = Path('/') / relative
        if item['kind'] == 'symlink':
            assert path.is_symlink() and os.readlink(path) == item['target']
        else:
            assert path.is_file() and not path.is_symlink()
            assert sha(path.read_bytes()) == item['sha256']
            assert stat.S_IMODE(path.stat().st_mode) == item['mode']
assert len(expected) == 49
def records(data):
    result = {}
    for block in data.decode().split('\\n\\n'):
        named = [line[2:] for line in block.splitlines() if line.startswith('P:')]
        if named:
            assert len(named) == 1 and named[0] not in result
            result[named[0]] = block
    return result
old = records((transaction / 'installed-before-private.txt').read_bytes())
new = records(Path('/lib/apk/db/installed').read_bytes())
assert len(new) == 944 and set(old) == set(new)
assert all(old[name] == new[name] for name in old if name not in names)
assert all(old[name] != new[name] for name in names)
for package in manifest['packages']:
    assert 'V:' + package['version'] in new[package['name']].splitlines()
retained, replaced = [], []
for line in (root / 'k236-baseline/userspace-check.sha256').read_text().splitlines():
    assert line[64:66] in ['  ', ' *']
    relative = line[66:].lstrip('/')
    if relative in expected:
        replaced.append(relative)
    else:
        retained.append(line)
assert retained and replaced
(out / 'userspace-unmodified-private.sha256').write_text('\\n'.join(retained) + '\\n')
(out / 'userspace-transaction-paths-private.json').write_text(json.dumps(replaced, indent=2) + '\\n')
checked(['sha256sum', '-c', str(out / 'userspace-unmodified-private.sha256')], 'userspace-unmodified')
checked(['sha256sum', '-c', str(root / 'k235-module-stage/loader-config-after.sha256')], 'loader-config')
assert stat.S_IMODE(Path('/etc/libcamera').stat().st_mode) == 0o755
assert not any(Path('/etc/libcamera').glob('*.apk-new'))
config = Path('/etc/libcamera/configuration.yaml').read_text()
assert 'mode: cpu' in config and 'dma_heap: system' in config
assert Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text() == 'ndx file:///var/lib/samurai/k239-r15-package-candidates/forward/packages.adb\\n'
wp = []
for proc in Path('/proc').glob('[0-9]*'):
    try:
        if (proc / 'comm').read_text().strip() == 'wireplumber':
            wp.append(proc)
    except OSError:
        pass
assert len(wp) == 1
maps = (wp[0] / 'maps').read_text()
camera_lines = [line for line in maps.splitlines() if '/usr/lib/libcamera' in line]
assert camera_lines and all('(deleted)' not in line for line in camera_lines)
assert any('/usr/lib/libcamera.so.' in line for line in camera_lines)
for line in camera_lines:
    path = line.split()[-1]
    assert sha(Path(path).read_bytes()) == expected[path.lstrip('/')]['sha256']
'''
replace(old, new)
replace("p.name.startswith(('k236', 'k238'))", "p.name.startswith(('k236', 'k238', 'k239'))")
replace('report = dict(stage=238,', 'report = dict(stage=239,')
replace('packages_userspace_loader_exact=True,',
        'packages_userspace_loader_exact_except_verified_seven_package_upgrade=True, installed_r15_r10=True, installed_payload_records=49, package_count=944, unrelated_package_records_unchanged=937, default_runtime_two_start_diagnostic_and_policy_reload_verified=True,')
replace('all238_workers_terminal=True, no238_mount_or_trace_left=True, no_scene_pixels_saved=True, rear_raw_48_controlled_frames_passed=True, rear_rgb_48_program_completed=True, rear_rgb_strict_acceptance_failed=True, rear_rgb_zero_queued_index=[1], r14_ram_candidate_not_installed=True, installed_r13_r8_preserved=True)',
        'all239_workers_terminal=True, no239_mount_or_trace_left=True, no_scene_pixels_saved=True, paired_raw_rgb_twelve_requests_complete=True, front_raw_rgb_six_each_passed=True, installed_rear_rgb_two_starts_24_frames_complete=True, rear_rgb_strict_acceptance_failed=True, scene_optical_response_and_colour_open=True, old_r13_r8_rollback_payloads_preserved=True, no_new_gnss_search_or_set=True)')
(R / 'final-health.py').write_text(source)
runner = '''from pathlib import Path
import json
import host
R = Path(__file__).resolve().parent
for name in ['r15-startup-analysis.json', 'r15-installed-startup-analysis.json']:
    report = json.loads((R / name).read_text())
    assert report['initial_parameters_correct_on_both_starts']
    assert report['every_processing_identity_matches_callback_sequence_timestamp']
result = host.ssh('python3 -', input=(R / 'final-health.py').read_bytes(), timeout=110)
(host.PRIVATE / 'final-health-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(R / 'final-health-validation.json').write_text(json.dumps(report, indent=2) + '\\n')
print(json.dumps(report))
'''
(R / 'run-final-health.py').write_text(runner)
compile(source, 'final-health.py', 'exec')
compile(runner, 'run-final-health.py', 'exec')
print('239 scoped r15 closure prepared; strict black-frame failures retained')
