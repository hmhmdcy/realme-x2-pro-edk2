from pathlib import Path
import hashlib, json, sys, tarfile

ref = Path(__file__).parent
private = Path(sys.argv[1])
def extract(archive, member):
    p = private / archive
    with tarfile.open(p) as t:
        report = json.loads(t.extractfile(member).read())
    report['archive_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    return report

runtime = extract('k171-runtime-private.tar.gz', 'k171-runtime/validation.json')
final = extract('k171-final-private.tar.gz', 'k171-final/validation.json')
assert runtime['new_boot_vs_preflash'] and runtime['speaker_sd_line'] == 1 and runtime['taint'] == 0
assert final['same_boot_as_k171_runtime'] and final['final_amplifiers_off'] and final['taint'] == 0
assert all(final['original_k171_mixer_controls_restored'].values()) and not final['test_pcm_processes_present']
q = json.loads((private / 'quiesce-validation.json').read_text(encoding='utf-8-sig'))
q.pop('boot_id')
assert q['quiesce_audit_pass'] and q['dma_prepare_before'] == q['dma_prepare_after'] == 0
tests = []
for label in ['dmic0-sd1-low48', 'dmic0-sd1-low36', 'dmic0-sd1-low24', 'dmic1-sd1-low24', 'dmic2-sd1-low24']:
    analysis = json.loads((ref / (label + '-analysis.json')).read_text())
    capture = extract('k171-' + label + '-private.tar.gz', 'k171-' + label + '/capture-validation.json')
    assert analysis['archive_sha256'] == capture['archive_sha256']
    assert len(capture['cases']) == 4 and all(c['capture_frames'] == 288000 for c in capture['cases'])
    assert capture['mixer_restored'] and capture['all_final_amplifiers_off'] and capture['amp_gain_unchanged']
    assert capture['same_boot'] and capture['taint'] == 0 and all(v == 0 for v in capture['fault_delta'].values())
    if analysis['tone_peak_dbfs'] == -24:
        assert all(r['known_tone_detected_with_disabled_amp_control'] for r in analysis['speaker_decisions'])
    tests.append(dict(label=label, capture_input=analysis['capture_input'], tone_peak_dbfs=analysis['tone_peak_dbfs'],
                      speaker_decisions=analysis['speaker_decisions'], complete_pcm_cases=4,
                      clipping_after_half_second=sum(r['clipped_samples_after_half_second'] for r in analysis['results']),
                      archive_sha256=analysis['archive_sha256']))
desktop = json.loads((ref / 'desktop-acoustic-validation.json').read_text())
assert all(r['detected_with_native_amp_off_reference'] for r in desktop['results'])
assert desktop['global_sink_volume_and_mute_verified_unchanged'] and desktop['same_boot']
baseline = json.loads((ref.parent / 'kernel170/dmic0-low24-pins-analysis.json').read_text())
assert not any(r['known_tone_detected_with_disabled_amp_control'] for r in baseline['speaker_decisions'])
summary = dict(stage=171, kernel_build=168, boot_and_logdump_generation=171,
               defect='Speaker RX was routed to SD0/GPIO139; board/OEM contract requires SD1/GPIO140',
               native_pcm_complete_cases=20, desktop_pcm_complete_cases=2,
               native_tests=tests,
               same_amplitude_prior_sd0_baseline=baseline['speaker_decisions'],
               prior_sd0_baseline_archive_sha256=baseline['archive_sha256'],
               native_left_and_right_tones_detected_on_all_three_dmic_inputs_at_minus24_dbfs=True,
               desktop_left_and_right_coded_tones_detected=True, detector_thresholds_unchanged=True,
               amp_gain_and_protection_unchanged=True,
               listening_quality_earphones_voice_quality_cold_boot_suspend_long_term_not_complete=True,
               physical_headphone_insertion_not_performed=True,
               human_listening_confirmation_pending=True,
               microphone_detected_tone_is_stronger_evidence_than_nonzero_noise=True,
               taint=final['taint'], fault_counts=final['fault_counts'])
for name, report in [('runtime-validation.json', runtime), ('final-validation.json', final),
                     ('shutdown-validation.json', q), ('acoustic-validation.json', summary)]:
    (ref / name).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(native_cases=20, desktop_cases=2, all_three_mics_both_tones_detected=True,
                      same_boot=final['same_boot_as_k171_runtime'], taint=final['taint'])))
