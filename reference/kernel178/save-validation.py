from pathlib import Path
import hashlib, json, tarfile

ref = Path(__file__).resolve().parent
out = Path('E:/edk2-samurai-out/kernel178')
archive = out / 'k178-all-private.tar.gz'
with tarfile.open(archive) as ar:
    for src, dst in [('k178-adsp-restart/validation.json', 'adsp-restart-validation.json'),
                     ('k178-adsp-restart/failure-audit.json', 'restart-failure-audit.json'),
                     ('k178-final/validation.json', 'final-validation.json')]:
        row = json.loads(ar.extractfile(src).read())
        assert row['stage'] == 178 and row['kernel_build'] == 176
        (ref / dst).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
native = json.loads((ref / 'dmic0-ucm178-low24-analysis.json').read_text())
desktop = json.loads((ref / 'desktop-acoustic-validation.json').read_text())
final = json.loads((ref / 'final-validation.json').read_text())
history_path = ref / 'known-failure-history.json'
history = json.loads(history_path.read_text()) if history_path.exists() else None
assert all(r['known_tone_detected_with_disabled_amp_control'] for r in native['speaker_decisions'])
assert all(r['detected_with_native_amp_off_reference'] for r in desktop['results'])
assert not any(final['postfailure_acoustic_window_fault_counts'].values())
report = dict(stage=178, kernel_build=176, related_model_sources_rechecked=True,
              controlled_adsp_restart_passed=False, failure_counts=final['known_failed_restart_counts'],
              after_failure_native_and_desktop_left_and_right_coded_tones_detected=True,
              latest_acoustic_window_fault_counts_zero=True, current_taint=final['taint'],
              final_uptime_seconds=final['uptime_seconds'], all_audio_goal_requirements_not_achieved=True,
              new_kernel_changes_or_flash=False, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              next_investigation=['WCD parent IRQ quiescence before child cleanup',
                                  'PDR list_lock across QMI wait and stale server/status generations'])
if history:
    report['captured_restart_fault_lower_bound'] = {k: v['unique_captured_log_lines'] for k, v in history['unique_fault_history'].items()}
    report['pre_restart_captured_fault_counts'] = history['pre_restart_fault_counts']
(ref / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
