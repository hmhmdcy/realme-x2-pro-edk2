"""Check saved receipts and source syntax without running GPU workloads."""
from pathlib import Path, PurePosixPath
import ast, hashlib, json, tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel148')
private=Path('/mnt/e/edk2-samurai-out/kernel148')
for f in ref.glob('*.py'):ast.parse(f.read_text(),filename=str(f))
for f in ref.glob('*.json'):json.loads(f.read_text())
report=json.loads((ref/'vulkan-validation.json').read_text())
assert report['status']=='closed_out' and not report['new_fault_seen']
assert not report['candidate_promoted'] and report['original_fault_reproduced'] is False
assert len(report['tests'])==36
assert report['successful_test_runs']==32 and report['failed_test_runs']==4
for row in report['tests']:
    assert row['before']['gpu_faults']==row['after']['gpu_faults']==1
    assert row['taint']=='0' and row['failed_bind_ops']==0
    assert row['boot_preserved'] and row['desktop_preserved']
for label in ['baseline-cube','baseline-cube-on']:
    row=next(t for t in report['tests'] if t['label']==label)
    assert row['early_timeout_delay_report_corrected'] and row['delayed_observation_seconds']==0
old=next(t for t in report['tests'] if t['label']=='candidate-capture-old-r2')
assert old['unaligned64k_maps']==2 and len(old['capture_replay_checks'])==2
assert all(t['external'] and t['mismatches']==0 for t in old['capture_replay_checks'])
for label in ['baseline-autotune-churn','candidate-autotune-churn']:
    row=next(t for t in report['tests'] if t['label']==label)
    assert row['exit']==0 and row['pixel_check']['pixels']==27221784
    assert row['successful_maps']==row['successful_unmaps']==242
    commands=json.loads((ref/(label+'-command-validation.json')).read_text())
    assert commands['decoded_through_frame']==12
    assert commands['bin_render_start']==447 and commands['bin_resolve']==6
for label in ['baseline-settings-phone-layout','candidate-settings-phone-layout','installed-settings-auto-phone-layout','candidate-settings-auto-phone-layout']:
    row=next(t for t in report['tests'] if t['label']==label)
    assert row['settings_cleanup']['graceful_quit'] and row['settings_cleanup']['process_exit']==0
    assert row['session_app_result']['exit']==0

bundle=private/'closeout-receipts-private.tar.gz'
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==bundle.with_name(bundle.name+'.sha256').read_text().strip()
with tarfile.open(bundle) as t:
    members={m.name:m for m in t}
    assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in members)
    sums=t.extractfile('k148-closeout/SHA256SUMS').read().decode().splitlines()
    for line in sums:
        digest,relative=line.split('  ',1)
        contents=t.extractfile('k148-closeout/'+relative.removeprefix('./')).read()
        assert hashlib.sha256(contents).hexdigest()==digest
closeout=json.loads((ref/'closeout.json').read_text())
assert not closeout['gpu_fix_complete'] and not closeout['candidate_promoted']
assert closeout['active_test_processes']==closeout['remaining_test_trace_instances']==0
assert closeout['watcher']['active'] is False and closeout['watcher']['cores_saved']==0
assert report['closeout']==closeout
final=json.loads((ref/'closeout-final-check.json').read_text())
assert final['fresh_boot_and_desktop_preserved'] and final['public_summary_persisted_and_hash_verified']
assert final['cumulative_fault_counts']==closeout['cumulative_fault_counts']
assert final['active_test_processes']==final['remaining_test_trace_instances']==0
index=json.loads((private/'archive-index-private.json').read_text())
host_archives=0
for row in index:
    path=private/(row['label']+'-private.tar.gz')
    if path.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        host_archives+=1
assert len(index)==37 and host_archives==24
for kind,digest in closeout['diagnostic_libraries_sha256'].items():
    assert hashlib.sha256((private/('libvulkan_freedreno-'+kind+'.so')).read_bytes()).hexdigest()==digest
summary=dict(source_syntax_checked=len(list(ref.glob('*.py'))),public_json_checked=len(list(ref.glob('*.json'))),
    test_receipts_checked=36,receipt_bundle_hash_and_manifest_verified=True,
    default_autotune_limited_command_decodes_verified=True,
    verified_host_raw_archives=host_archives,persistent_phone_raw_archives=len(index),
    diagnostic_libraries_verified=True,final_device_check_verified=True)
(ref/'closeout-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
