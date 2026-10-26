from pathlib import Path
import hashlib, json, tarfile

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
def report_from_archive(path, name):
    with tarfile.open(path) as archive:
        return json.load(archive.extractfile(name))
def save(name, value):
    (ref / name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
runtime = report_from_archive(out / 'k172-runtime-private.tar.gz','k172-runtime/validation.json')
final = report_from_archive(out / 'k172-final-private.tar.gz','k172-final/validation.json')
assert runtime['kernel_build'] == final['kernel_build'] == 172
assert runtime['new_boot_vs_preflash'] and final['same_boot_as_k172_runtime']
assert runtime['nv_check_pass'] and final['nv_verified'] and final['modules132_verified']
assert final['taint'] == 0 and all(v == 0 for v in final['fault_counts'].values())
assert all(v == 'closed' for v in final['pcm'].values()) and final['final_amplifiers_off']
assert final['jack_bound_once'] and all(v == 'off' for v in final['jack_status'].values())
save('runtime-validation.json',runtime); save('final-validation.json',final)
build = json.loads((ref / 'build-package-validation.json').read_text())
assert runtime['partition_hashes']['/dev/sde11'] == build['boot_sha256']
assert runtime['partition_hashes']['/dev/sde32'] == build['logdump_sha256']
q = json.loads((out / 'quiesce-validation.json').read_text()); q.pop('boot_id')
assert q['dma_prepare_before'] == q['dma_prepare_after'] == 0 and q['quiesce_audit_pass']
q['checker_upload_name_corrected_without_repeating_quiesce'] = True
save('shutdown-validation.json',q)
events = [json.loads(l) for l in (out / 'headset-first-f1-wsl.events.jsonl').read_text().splitlines()]
assert sum(e['event'] == 'out_submit' for e in events) == sum(e['event'] == 'receipt' and e['text'] == 'F1' for e in events) == 1
deployment = dict(stage=172, flash_partitions=['boot','logdump'], current_kernel_build=172,
                  fresh_source_boot_checked=True, old_boot_and_logdump171_rollback_bytes_preserved=True,
                  single_f1_receipt=True, usb_eio_after_f1_preserved=True,
                  boot_logdump_full_readback_matches=True, persist_nv_unchanged=True,
                  initial_runtime_collector_assumed_combined_card_control_corrected=True,
                  actual_card_controls=['Headphone Jack','Mic Jack'],
                  initial_missing_checker_upload_corrected=True, repeated_transition=False,
                  hardware_headset_insertion_test_pending=True, ucm132_not_changed=True)
save('deployment-validation.json',deployment)
native = json.loads((ref / 'dmic0-sd1-low24-analysis.json').read_text())
desktop = json.loads((ref / 'desktop-acoustic-validation.json').read_text())
assert all(d['known_tone_detected_with_disabled_amp_control'] for d in native['speaker_decisions'])
assert all(d['detected_with_native_amp_off_reference'] for d in desktop['results'])
save('acoustic-validation.json',dict(stage=172, native_case_count=4, desktop_case_count=2,
    native_left_right_correlations=[d['active_code_correlation'] for d in native['speaker_decisions']],
    native_amp_on_off_difference_db=[d['active_to_disabled_tone_band_db'] for d in native['speaker_decisions']],
    desktop_left_right_correlations=[d['best_code_energy_correlation'] for d in desktop['results']],
    desktop_against_same_boot_native_amp_off_reference=True, all_detected=True,
    human_listening_confirmation_belongs_to_prior171_replay=True,
    full_audio_quality_and_headset_not_accepted=True))
home = report_from_archive(out.parent / 'kernel171/k171-home-final-private.tar.gz','k171-home-final/validation.json')
(ref.parent / 'kernel171/home-final-validation.json').write_text(json.dumps(home,indent=2)+'\n')
print('K172_EVIDENCE_SUMMARIZED_WITHOUT_BOOT_IDENTIFIERS',flush=True)
