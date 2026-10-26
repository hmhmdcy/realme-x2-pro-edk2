"""Use matched amp-off controls in the original recording after recovery."""
from pathlib import Path
import ast
import hashlib
import io
import json
import math
import sys
import tarfile
import wave
import numpy as np

ref = Path(__file__).resolve().parent
archive, runtime_archive = map(Path, sys.argv[1:3])
node = next(n for n in ast.parse((ref.parent / 'kernel181/analyze-acoustic.py').read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'analyze_samples')
ns = dict(np=np, math=math)
exec(compile(ast.Module(body=[node], type_ignores=[]), 'same-181-detector', 'exec'), ns)
with tarfile.open(archive) as t, tarfile.open(runtime_archive) as runtime:
    prefix = 'k183-playback-crash-fixed-v2/'
    report = json.loads(t.extractfile(prefix + 'validation.json').read())
    assert report['kernel_build'] == 183 and report['same_boot'] and report['taint'] == 0
    assert not any(report['fault_counts'].values())
    assert t.extractfile(prefix + 'boot-id-private.txt').read() == runtime.extractfile('k183-runtime/boot-id-private.txt').read()
    with wave.open(io.BytesIO(t.extractfile(prefix + 'original-capture-private.wav').read())) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
        data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
    stimulus = dict(code=[1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0], leading_silence_seconds=.5)
    rows = []; pairs = {}
    for job in report['jobs'][1:]:
        case = dict(case=job['case'], speaker=job['speaker'], frequency=997 if job['speaker'] == 'left' else 1511,
                    target_speaker_enabled=job['target_speaker_enabled'], play_start_after_capture_seconds=job['raw_position_seconds'])
        row, _, on, off = ns['analyze_samples'](data, case, stimulus)
        rows.append(row); pairs[(job['speaker'], job['target_speaker_enabled'])] = (row, on)
    decisions = []
    for speaker in ['left', 'right']:
        (positive, on), (negative, disabled) = pairs[(speaker, True)], pairs[(speaker, False)]
        ratio = 10 * math.log10(max(on, 1e-12) / max(disabled, 1e-12))
        decisions.append(dict(speaker=speaker, active_correlation=positive['best_code_energy_correlation'],
                              disabled_correlation=negative['best_code_energy_correlation'],
                              active_on_off_db=positive['on_to_off_band_power_db'],
                              active_to_disabled_band_db=ratio,
                              detected=positive['best_code_energy_correlation'] >= .75
                              and positive['on_to_off_band_power_db'] >= 6 and ratio >= 8))
    report.update(acoustic_analysis_pending=False, acoustic_results=rows, speaker_decisions=decisions,
                  original_stream_matched_amp_off_controls=True,
                  hardware_global_and_amp_enable_bits_checked_for_amp_off=True,
                  first_fixed_test_mute_flag_harness_failure_preserved=True, old_boot_native_control_not_used_for_detection=True,
                  driver_fault_free_pass=True, detector_identical_to181=True,
                  thresholds=dict(correlation=.75, on_off_db=6, amp_off_reference_db=8),
                  human_quality_and_lossless_crash_continuity_not_verified=True,
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    assert len(rows) == 4 and all(r['clipped_samples_after_half_second'] == 0 for r in rows)
    assert all(d['detected'] for d in decisions), decisions
    (ref / 'playback-crash-fixed-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(kernel_build=183, driver_fault_free_pass=True, speaker_decisions=decisions), indent=2))
