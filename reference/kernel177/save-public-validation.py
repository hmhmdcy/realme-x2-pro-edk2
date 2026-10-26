from pathlib import Path
import hashlib, json, tarfile
import numpy as np

ref = Path(__file__).resolve().parent
out = Path('E:/edk2-samurai-out/kernel177')
archive = out / 'k177-all-private.tar.gz'
reports = {'k177-rtc/validation.json': 'rtc-validation.json',
           'k177-suspend-idle/validation.json': 'suspend-idle-validation.json',
           'k177-suspend-active/validation.json': 'suspend-active-validation.json',
           'k177-runtime/validation.json': 'runtime-validation.json',
           'k177-stop/validation.json': 'capture-stop-validation.json',
           'k177-final/validation.json': 'final-validation.json'}
with tarfile.open(archive) as ar:
    for src, dst in reports.items():
        row = json.loads(ar.extractfile(src).read())
        assert row['stage'] == 177 and row['kernel_build'] == 176 and row['taint'] == 0
        (ref / dst).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
        (out / dst).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
    samples = np.frombuffer(ar.extractfile('k177-suspend-active/active-capture-private.raw').read(), dtype='<i2')
    zero = samples == 0
    edges = np.diff(np.r_[False, zero, False].astype(np.int8))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    longest = int(np.argmax(ends - starts))
    continuity = dict(stage=177, kernel_build=176, sample_rate=48000, capture_frames=len(samples),
                      captured_duration_seconds=len(samples)/48000, exact_zero_fraction=float(zero.mean()),
                      longest_exact_zero_run_samples=int(ends[longest]-starts[longest]),
                      longest_exact_zero_run_seconds=float((ends[longest]-starts[longest])/48000),
                      longest_zero_run_start_seconds=float(starts[longest]/48000),
                      uninterrupted_capture_through_system_sleep_not_proven=True,
                      software_silence_insertion_vs_hardware_cause_not_measured=True)
(ref / 'active-capture-continuity.json').write_text(json.dumps(continuity, indent=2) + '\n', encoding='utf-8')
native = json.loads((ref / 'dmic0-ucm177-low24-analysis.json').read_text())
desktop = json.loads((ref / 'desktop-acoustic-validation.json').read_text())
final = json.loads((ref / 'final-validation.json').read_text())
assert all(r['known_tone_detected_with_disabled_amp_control'] for r in native['speaker_decisions'])
assert all(r['detected_with_native_amp_off_reference'] for r in desktop['results'])
assert not any(final['fault_counts'].values())
report = dict(stage=177, kernel_build=176, new_kernel_build_or_flash=False,
              idle_and_active_system_s2idle_rtc_resume_passed=True, system_suspend_successes=2, system_suspend_failures=0,
              same_boot_and_no_manual_driver_rebind=True, all_pm_callback_end_errors_zero=True,
              post_resume_native_and_desktop_left_and_right_tones_detected=True, capture_stop_cases=8, pause_cycles=3,
              final_uptime_seconds=final['uptime_seconds'], final_taint=0,
              observed_audio_fault_counts_zero=True, non_audio_log_observations=final['non_audio_log_observations'],
              active_capture_continuity=continuity, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              complete_audio_goal_not_achieved=True,
              remaining=['physical headphone/headset and buttons', 'SSR and repeated/longer PM restoration',
                         'cold startup and long-term reliability', 'audio quality, transients and speaker protection'],
              test_scope_does_not_assert_lossless_or_uninterrupted_audio_during_system_sleep=True)
(ref / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(out / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
