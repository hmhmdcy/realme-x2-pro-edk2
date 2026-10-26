"""Analyze the saved single crash experiment; never inject another crash."""
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
archive, native_archive = map(Path, sys.argv[1:3])
source = (ref.parent / 'kernel181/analyze-acoustic.py').read_text(encoding='utf-8')
node = next(n for n in ast.parse(source).body
            if isinstance(n, ast.FunctionDef) and n.name == 'analyze_samples')
ns = dict(np=np, math=math)
exec(compile(ast.Module(body=[node], type_ignores=[]), 'same-181-detector', 'exec'), ns)
with tarfile.open(archive) as t, tarfile.open(native_archive) as native:
    read = lambda name: t.extractfile('k182-active-crash/' + name).read()
    report = json.loads(read('validation.json'))
    assert report['kernel_build'] == 181 and report['same_boot'] and report['taint'] == 0
    assert report['original_parecord_survived'] and report['postrecovery_tone_played']
    assert not any(report['fault_counts'].values())
    assert b'Traceback' not in t.extractfile('k182-active-crash-worker-private.log').read()
    prefix = 'k181-dmic0-ucm181-low24/'
    assert read('boot-id-private.txt') == native.extractfile(prefix + 'boot-id-private.txt').read()
    stimulus = json.loads(native.extractfile(prefix + 'capture-validation.json').read())
    with wave.open(io.BytesIO(read('active-capture-private.wav'))) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
        data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
    case = dict(case='original-recording-after-crash', speaker='right', frequency=1511,
                target_speaker_enabled=True,
                play_start_after_capture_seconds=report['postrecovery_tone_raw_position_estimate_seconds'])
    row, amplitude, on, off = ns['analyze_samples'](data, case, stimulus)
    negative = next(r for r in json.loads((ref.parent / 'kernel181/dmic0-ucm181-low24-analysis.json')
                                        .read_text())['results'] if r['case'] == 'right-off-control')
    ratio = 20 * math.log10(max(row['code_on_band_rms_pcm_counts'], 1e-12)
                          / negative['code_on_band_rms_pcm_counts'])
    row.update(active_to_same_boot_native_amp_disabled_db=ratio,
               detected=row['best_code_energy_correlation'] >= .75
               and row['on_to_off_band_power_db'] >= 6 and ratio >= 8)
    before = json.loads(read('source-outputs-before-private.json'))
    after = json.loads(read('source-outputs-after-recovery-private.json'))
    sources = json.loads(read('sources-after-recovery-private.json'))
    old_sources = json.loads(read('sources-before-private.json'))
    assert len(before) == len(after) == 1 and before[0]['index'] == after[0]['index']
    mic = next(s for s in sources if s['name'] == 'alsa_input.platform-sound.HiFi__Mic__source')
    old_mic = next(s for s in old_sources if s['name'] == mic['name'])
    assert old_mic['volume'] == mic['volume'] and old_mic['mute'] == mic['mute']
    assert after[0]['source'] == mic['index'] and after[0]['corked'] is False
    timeline = json.loads(read('timeline-private.json'))
    removed = next(s for s in timeline if not s['maps'] and 'Realme X2 Pro' not in s['cards'])
    restored = next(s for s in timeline if s['t'] > removed['t'] and len(s['maps']) == 2
                    and 'Realme X2 Pro' in s['cards'])
    running = next(s for s in timeline if s['t'] >= restored['t'] and 'RUNNING' in s['capture'])
    # The original field was measured after paplay and the trailing one-second wait.
    # Preserve that raw report and correct only the derived public field name.
    report['crash_to_after_playback_and_wait_elapsed_seconds'] = report.pop('recovery_latency_seconds')
    report.update(original_source_output_reconnected_to_rebuilt_mic=True,
                  source_volume_and_mute_verified_unchanged=True,
                  observed_card_resource_gap_seconds=restored['t'] - removed['t'],
                  observed_capture_running_after_resource_return_seconds=running['t'] - restored['t'],
                  timeline_nominal_poll_interval_seconds=.025,
                  timing_original_raw_field_misnamed_recovery_latency=True,
                  raw_report_preserved=True, acoustic_result=row,
                  detector_identical_to181=True,
                  thresholds=dict(correlation=.75, on_off_db=6, amp_off_reference_db=8),
                  reference='Same-boot 181 native target-amplifier-disabled recording',
                  independent_desktop_amp_off_control=False,
                  continuous_audio_during_crash_not_verified=True,
                  raw_sample_position_is_not_wall_clock_time=True,
                  archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  native_reference_archive_sha256=hashlib.sha256(native_archive.read_bytes()).hexdigest())
    assert report['recorded_frames'] == len(data)
    assert row['detected'] and row['clipped_samples_after_half_second'] == 0
    for output in [ref / 'active-crash-validation.json', archive.parent / 'active-crash-validation.json']:
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, acoustic=row,
                         card_resource_gap_seconds=report['observed_card_resource_gap_seconds'],
                         capture_after_resource_seconds=report['observed_capture_running_after_resource_return_seconds']), indent=2))
