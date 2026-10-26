from pathlib import Path
import ast, hashlib, io, json, math, sys, tarfile, wave
import numpy as np

ref = Path(__file__).parent
archive = Path(sys.argv[1])
node = next(n for n in ast.parse((ref / 'analyze-acoustic.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'analyze_samples')
ns = dict(np=np, math=math)
exec(compile(ast.Module(body=[node], type_ignores=[]), 'same-tone-detector', 'exec'), ns)
control = json.loads((ref / 'dmic0-ucm183-low24-analysis.json').read_text())
rows = []
with tarfile.open(archive) as t:
    report = json.loads(t.extractfile('k183-desktop/validation.json').read())
    pulse_before = json.loads(t.extractfile('k183-desktop/pulse-before-private.json').read())
    pulse_after = json.loads(t.extractfile('k183-desktop/pulse-after-private.json').read())
    sink = lambda data: next(s for s in data if s['name'] == 'alsa_output.platform-sound.HiFi__Speaker__sink')
    old_sink, new_sink = sink(pulse_before), sink(pulse_after)
    assert old_sink['volume'] == new_sink['volume'] and old_sink['mute'] == new_sink['mute']
    source_before = json.loads(t.extractfile('k183-desktop/source-before-private.json').read())
    source_after = json.loads(t.extractfile('k183-desktop/source-after-private.json').read())
    mic = lambda data: next(s for s in data if s['name'] == 'alsa_input.platform-sound.HiFi__Mic__source')
    assert mic(source_before)['volume'] == mic(source_after)['volume'] and mic(source_before)['mute'] == mic(source_after)['mute']
    for case in report['cases']:
        with wave.open(io.BytesIO(t.extractfile('k183-desktop/' + case['case'] + '-capture-private.wav').read()), 'rb') as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 48000)
            data = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64)
        row, amplitude, on, off = ns['analyze_samples'](data, case, report)
        negative = next(r for r in control['results'] if r['case'] == case['speaker'] + '-off-control')
        ratio = 20 * math.log10(max(row['code_on_band_rms_pcm_counts'], 1e-12) / negative['code_on_band_rms_pcm_counts'])
        row.update(desktop_to_native_amp_disabled_tone_band_db=ratio,
                   detected_with_native_amp_off_reference=row['best_code_energy_correlation'] >= .75 and
                       row['on_to_off_band_power_db'] >= 6 and ratio >= 8)
        rows.append(row)
summary = dict(stage=183, kernel_build=183, playback_api='PulseAudio paplay through user speaker sink',
               capture_api='PulseAudio parecord through user Mic source', source_volume_and_mute_verified_unchanged=True,
               capture_input='DMIC0', results=rows, mixer_restored=report['mixer_restored'],
               taint=report['taint'], fault_delta=report['fault_delta'],
               amplifiers_off=report['final_amplifiers_off'], pcm_closed=report['final_pcm_closed'],
               same_boot=report['same_boot'], global_sink_volume_not_changed=report['global_sink_volume_not_changed'],
               global_sink_volume_and_mute_verified_unchanged=True,
               reference_control='Prior native PCM target-amplifier-disabled capture at identical frequencies in the same boot',
               human_listening_and_calibrated_quality_not_verified=True,
               archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(ref / 'desktop-acoustic-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
(archive.parent / 'desktop-acoustic-validation.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
