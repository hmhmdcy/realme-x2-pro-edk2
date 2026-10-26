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
archive = Path(sys.argv[1])
node = next(n for n in ast.parse((ref.parent / 'kernel181/analyze-acoustic.py').read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == 'analyze_samples')
ns = dict(np=np, math=math)
exec(compile(ast.Module(body=[node], type_ignores=[]), 'same-181-detector', 'exec'), ns)
control = json.loads((ref.parent / 'kernel181/dmic0-ucm181-low24-analysis.json').read_text())
with tarfile.open(archive) as t:
    prefix = 'k183-playback-crash/'
    report = json.loads(t.extractfile(prefix + 'validation.json').read())
    assert report['kernel_build'] == 181 and report['same_boot'] and report['taint'] == 0
    assert report['fault_counts']['asoc'] == 3
    assert not any(v for k, v in report['fault_counts'].items() if k != 'asoc')
    with tarfile.open(archive.parent.parent / 'kernel181/k181-dmic0-ucm181-low24-private.tar.gz') as native:
        native_prefix = 'k181-dmic0-ucm181-low24/'
        assert t.extractfile(prefix + 'boot-id-private.txt').read() == native.extractfile(native_prefix + 'boot-id-private.txt').read()
        stimulus = json.loads(native.extractfile(native_prefix + 'capture-validation.json').read())
    with wave.open(io.BytesIO(t.extractfile(prefix + 'original-capture-private.wav').read())) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
        data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
    rows = []
    for job in report['jobs'][1:]:
        case = dict(case=job['case'], speaker=job['speaker'], frequency=997 if job['speaker'] == 'left' else 1511,
                    target_speaker_enabled=True, play_start_after_capture_seconds=job['raw_position_seconds'])
        row, _, _, _ = ns['analyze_samples'](data, case, stimulus)
        negative = next(r for r in control['results'] if r['case'] == job['speaker'] + '-off-control')
        ratio = 20 * math.log10(max(row['code_on_band_rms_pcm_counts'], 1e-12) / negative['code_on_band_rms_pcm_counts'])
        row.update(active_to_same_boot_native_amp_disabled_db=ratio,
                   detected=row['best_code_energy_correlation'] >= .75 and row['on_to_off_band_power_db'] >= 6 and ratio >= 8)
        rows.append(row)
    report.update(acoustic_analysis_pending=False, acoustic_results=rows,
                  acoustic_channels_passed=all(r['detected'] and r['clipped_samples_after_half_second'] == 0 for r in rows),
                  driver_fault_free_pass=False, known_failure='WCD934x STOP -ENOTCONN plus three ASoC errors during transport loss',
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  detector_identical_to181=True, thresholds=dict(correlation=.75, on_off_db=6, amp_off_reference_db=8),
                  native_amp_off_reference_in_same_boot=True, independent_desktop_amp_off_control=False,
                  no_lossless_crash_continuity_or_human_quality_claim=True)
    (ref / 'playback-crash-before-fix-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(acoustic_results=rows, acoustic_channels_passed=report['acoustic_channels_passed'],
                         driver_fault_free_pass=False), indent=2))
