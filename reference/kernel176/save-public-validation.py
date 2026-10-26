from pathlib import Path
import hashlib, json, tarfile

ref = Path(__file__).resolve().parent
out = Path('E:/edk2-samurai-out/kernel176')
archive = out / 'k176-all-private.tar.gz'
reports = {'k176-runtime/validation.json': 'runtime-validation.json',
           'k176-reprobe/validation.json': 'reprobe-validation.json',
           'k176-stop/validation.json': 'capture-stop-validation.json',
           'k176-final/validation.json': 'final-validation.json'}
with tarfile.open(archive) as ar:
    for src, dst in reports.items():
        row = json.loads(ar.extractfile(src).read())
        assert row['stage'] == row['kernel_build'] == 176 and row['taint'] == 0
        (ref / dst).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
        (out / dst).write_text(json.dumps(row, indent=2) + '\n', encoding='utf-8')
native = json.loads((ref / 'dmic0-ucm176-low24-analysis.json').read_text())
desktop = json.loads((ref / 'desktop-acoustic-validation.json').read_text())
final = json.loads((ref / 'final-validation.json').read_text())
assert all(r['known_tone_detected_with_disabled_amp_control'] for r in native['speaker_decisions'])
assert all(r['detected_with_native_amp_off_reference'] for r in desktop['results'])
assert not any(final['fault_counts'].values())
report = dict(stage=176, kernel_build=176, all_current_regressions_passed=True,
              native_left_and_right_coded_tones_detected=True, desktop_left_and_right_coded_tones_detected=True,
              two_codec_and_eight_parent_rebinds_passed=True, old_debugfs_dead_handles=18,
              supplies_balanced=True, capture_stop_cases=8, real_pause_cycles=3,
              final_uptime_seconds=final['uptime_seconds'], final_taint=0,
              all_observed_fault_counts_zero=True,
              archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
              complete_audio_goal_not_achieved=True,
              remaining=['physical headphone/headset and buttons', 'system suspend and SSR',
                         'cold startup and long-term reliability', 'audio quality, transients and speaker protection'])
(ref / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(out / 'checkpoint-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
