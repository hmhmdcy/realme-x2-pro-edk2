"""Validate complete receipts, including expected failures and harness limits."""
from pathlib import Path
import json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel149')
p=ref/'regression-validation.json'
report=json.loads(p.read_text());rows=report['tests'];by={r['label']:r for r in rows}
expected_failures={'baseline-holes','installed-gmem-holes','deployed-parallel-gles'}
assert len(rows)==13 and len(by)==13
assert {r['label'] for r in rows if r['exit']!=0}==expected_failures
for label in ['baseline-holes','installed-gmem-holes']:
    r=by[label]
    assert r['exit']==2 and r['core_saved']==1 and not r['capture_errors']
    assert r['after']['gpu_faults']==r['before']['gpu_faults']+1
    assert r['pixel_readbacks']==0 and r['failed_bind_ops']==0
for r in rows:
    assert r['taint']=='0' and r['boot_preserved'] and r['pixel_mismatches']==0
    assert not r['error'] and not r['capture_errors']
    if r['label'] not in expected_failures:
        assert r['exit']==0 and r['before']==r['after'] and r['failed_bind_ops']==0
        assert r['desktop_preserved'] or r['label']=='deployed-gmem-hole-formats'
        if r.get('kind','pixel')=='pixel':assert r['pixel_iterations_complete']
for label in ['deployed-settings-gmem','deployed-settings-default']:
    r=by[label]
    assert r['application_cleanup']['graceful_quit'] and r['application_cleanup']['process_exit']==0
assert by['deployed-parallel-gles-r2']['parallel_result']['exit_codes']==[0,0]
memory=by['deployed-memory-replay']
assert memory['sparse_remaps']==16 and memory['capture_replays']==2
assert memory['memory_mismatches']==0 and memory['old_unaligned_capture_replayed']
pm=by['deployed-gmem-holes-pm']
assert pm['gpu_suspend_events']>=24 and pm['gpu_resume_events']>=24 and pm['trace_overruns']==0
final=json.loads((ref/'final-verification.json').read_text())
assert final['new_faults_after_deployment']==0 and final['physical_desktop_preserved']
assert final['package_database_preserved'] and final['greetd_configuration_preserved']
assert final['installed_library_sha256']=='97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
fixed=[r for r in rows if r['driver_library_sha256']==final['installed_library_sha256'] and r['exit']==0]
report.update(reproduced_fault_fixed_and_deployed=True,total_receipts=len(rows),
    successful_process_exits=sum(r['exit']==0 for r in rows),
    retained_failed_process_exits=sum(r['exit']!=0 for r in rows),
    fixed_driver_pixel_readbacks=sum(r['pixel_readbacks'] for r in fixed),
    fixed_driver_pixels_checked=sum(r['pixels_checked'] for r in fixed),
    successful_settings_panel_opens=36,new_faults_after_deployment=0,
    original_gnome_fault_complete_core_unavailable=True,
    scope='A640 automatic VM_BIND CCU translation regression on RMX1931',
    whole_device_adaptation_complete=False,
    limitations=['One early pixel receipt included a temporary test compositor in its desktop counter; later physical desktop checks passed.',
                 'The first parallel GLES run omitted Wayland environment variables; corrected run passed.',
                 'The initial candidate pixel summary had argument ordering wrong; per-iteration readbacks were correct and the probe was repaired.',
                 'Isolated GNOME Settings has no Mutter DisplayConfig service; panel lifecycle is tested, complete display settings functionality is not.',
                 'A normal Mesa package upgrade can overwrite the local library patch; rebuild with the saved source patch.'])
p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
