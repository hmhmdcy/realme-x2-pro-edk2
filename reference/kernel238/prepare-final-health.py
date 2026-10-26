"""Prepare a scoped health check after RAM-only r14 experiments, retaining RGB failure."""
from pathlib import Path

R = Path(__file__).resolve().parent
source = (R.parent / 'kernel237/final-health.py').read_text()


def replace(old, new):
    global source
    assert source.count(old) == 1, old[:90]
    source = source.replace(old, new)


replace('"""Current237 CAMSS unwind plus rear RAW and front RAW/RGB health."""',
        '"""Current238 scoped health; RGB startup black-frame failure is retained."""')
replace("out = root / 'k237-final-health'", "out = root / 'k238-final-health'")
replace("for which, kind in [('rear','raw'),('front','raw'),('front','rgb')]:\n    assert json.loads((root / f'k237-capture-{which}-{kind}-r2/summary.json').read_text())['passed']", """contexts = ['k238-controlled-rear-r14', 'k238-controlled-rear-r14-r2',
            'k238-controlled-rear-rgb-r14', 'k238-controlled-rear-rgb-r14-r2',
            'k238-vendor-audit', 'k238-vendor-followup']
for name in contexts:
    assert json.loads((root / name / 'state-private.json').read_text())['state'] == 'terminal', name
raw = json.loads((root / 'k238-controlled-rear-r14-r2/summary.json').read_text())
rgb = json.loads((root / 'k238-controlled-rear-rgb-r14-r2/summary.json').read_text())
assert raw['passed'] and len(raw['frames']) == 48
assert not rgb['passed'] and rgb['program_exit'] == 0 and len(rgb['frames']) == 48
assert [f['queued_index'] for f in rgb['frames'] if f['all_zero']] == [1]
for report in [raw, rgb]:
    assert all(report[k] for k in ['all_formats_restored', 'media_graph_restored',
        'sensor_controls_restored', 'rails_unchanged', 'camera_devices_suspended',
        'mclk1_mclk2_disabled', 'trace_instance_removed'])
    assert not report['restore_errors'] and not any(report['fault_delta'].values())
for name in ['k238-vendor-audit', 'k238-vendor-followup']:
    summary = json.loads((root / name / 'summary.json').read_text())
    assert summary['unmounted'] and summary['vendor_before_after_equal']
assert not any('k238' in line for line in Path('/proc/self/mountinfo').read_text().splitlines())
assert not any(p.name.startswith('k238') for p in Path('/sys/kernel/tracing/instances').iterdir())
""")
# No partitions or kernel modules were changed by 238. Recheck the current
# module manifest and userspace; vendor-specific full block hashes are already
# retained by both read-only extraction workers, so do not repeat all partitions.
replace("checked(['sha256sum', '-c', str(root / 'k236-tools/partition-after.sha256')], 'partitions')\n", '')
replace("assert not Path('/sys/kernel/tracing/instances/k236_lab_probe').exists()", "assert not any(p.name.startswith(('k236', 'k238')) for p in Path('/sys/kernel/tracing/instances').iterdir())")
replace('report = dict(stage=237, same236_boot_verified=True, default_and_loaded_modules=modules,',
        'report = dict(stage=238, same236_boot_verified=True, default_and_loaded_modules=modules,')
replace('packages_userspace_loader_and_partitions_exact=True,',
        'packages_userspace_loader_exact=True, partitions_not_rehashed_in_this_scoped_check=True, vendor_readonly_audit_verified_separately=True,')
replace('first_lab_probe_error_not_erased=True, no_scene_pixels_saved=True, rear_raw_six_frames=True, front_raw_rgb_six_each=True)',
        'all238_workers_terminal=True, no238_mount_or_trace_left=True, no_scene_pixels_saved=True, rear_raw_48_controlled_frames_passed=True, rear_rgb_48_program_completed=True, rear_rgb_strict_acceptance_failed=True, rear_rgb_zero_queued_index=[1], r14_ram_candidate_not_installed=True, installed_r13_r8_preserved=True)')
(R / 'final-health.py').write_text(source)
runner = (R.parent / 'kernel237/run-final-health.py').read_text()
(R / 'run-final-health.py').write_text(runner)
print('238 scoped health prepared; RAW passes, RGB strict failure retained')
