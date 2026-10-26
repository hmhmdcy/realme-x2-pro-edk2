from pathlib import Path
import hashlib, json, sys, tarfile

private = Path(sys.argv[1])
public = Path(__file__).resolve().parent

def report_from_archive(name, member):
    archive = private / name
    with tarfile.open(archive) as t:
        report = json.loads(t.extractfile(member).read())
    report['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
    return report

route = report_from_archive('k170-active-route-private.tar.gz', 'k170-active-route/validation.json')
final = report_from_archive('k170-final-private.tar.gz', 'k170-final/validation.json')
assert final['same_boot_as_k169_final'] and final['taint'] == 0
assert not final['test_pcm_processes_present'] and final['final_amplifiers_off']
assert all(final['original_k170_mixer_controls_restored'].values())
tests = []
for label in ['dmic0-low48-r1', 'dmic0-low36', 'dmic2-low36', 'dmic1-low36-pins', 'dmic0-low24-pins']:
    capture = report_from_archive('k170-' + label + '-private.tar.gz', 'k170-' + label + '/capture-validation.json')
    analysis = json.loads((public / (label + '-analysis.json')).read_text())
    assert capture['archive_sha256'] == analysis['archive_sha256']
    assert len(capture['cases']) == 4 and all(c['capture_frames'] == 288000 for c in capture['cases'])
    assert capture['same_boot'] and capture['mixer_restored'] and capture['all_final_amplifiers_off']
    assert capture['amp_gain_unchanged'] and capture['taint'] == 0 and all(v == 0 for v in capture['fault_delta'].values())
    tests.append(dict(label=label, input=analysis['capture_input'], peak_dbfs=analysis['tone_peak_dbfs'],
                      successful_software_cases=4, capture_frames_per_case=288000,
                      speaker_decisions=analysis['speaker_decisions'],
                      clipped_samples_after_half_second=sum(c['clipped_samples_after_half_second'] for c in analysis['results']),
                      capture_archive_sha256=capture['archive_sha256']))
summary = dict(stage=170, kernel_build=168, deployment_unchanged_from_169=True,
               user_reported_placement='ordinary desk; no headphones',
               user_reported_sound_uncertain='may be computer fan; not a confirmed phone sound',
               method='Known coded tone; target amplifier enabled versus target disabled while identical PCM is still fed',
               tests=tests, completed_software_cases=sum(t['successful_software_cases'] for t in tests),
               any_coded_tone_detected=any(d['known_tone_detected_with_disabled_amp_control'] for t in tests for d in t['speaker_decisions']),
               result='No confident acoustic detection at the tested settings',
               independent_known_acoustic_source_for_microphone_not_tested=True,
               failure_not_localized_between_speaker_output_and_microphone_pickup=True,
               calibrated_sound_pressure_not_measured=True, gain_and_protection_unchanged=True,
               script_initial_boolean_argument_error_rejected_and_fixed=True,
               interrupted_low24_scp_partial_preserved_and_recovered=True,
               recovered_low24_archive_matches_phone_sha256=tests[-1]['capture_archive_sha256'] == 'e9b8760eeae6e1b32d196899cfa873a6fd73407772254bf8714675ccc80ada74')
assert summary['recovered_low24_archive_matches_phone_sha256']
for name, report in [('active-route-validation.json', route), ('final-validation.json', final), ('acoustic-validation.json', summary)]:
    (public / name).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(completed_software_cases=summary['completed_software_cases'],
                      acoustic_detection=summary['any_coded_tone_detected'],
                      playback_hw_ptr_advance=route['playback_hw_ptr_advance'],
                      same_boot=final['same_boot_as_k169_final'], taint=final['taint'])))
