from pathlib import Path
import hashlib
import json

here = Path(__file__).resolve().parent
a, b = [json.loads((here / ('loc-r3-' + name + '-validation.json')).read_text()) for name in ['default', 'high']]
assert a['binary_sha256'] == b['binary_sha256']
assert a['source_sha256'] == b['source_sha256'] == hashlib.sha256((here / 'loc-session.c').read_bytes()).hexdigest()
assert a['decoder_sha256'] == b['decoder_sha256'] == hashlib.sha256((here / 'loc_decode.py').read_bytes()).hexdigest()
start = lambda r: next(x['request_tlvs'] for x in r['commands'] if x['message_id'] == 0x22)
sa, sb = start(a), start(b)
assert '17' not in sa and sb['17'] == '03000000'
assert sa == {k: v for k, v in sb.items() if k != '17'}
assert sa == {'1': 'e2', '16': '01000000', '18': '02000000', '19': 'e8030000'}
criteria = lambda r: [x for x in r['commands'] if x['message_id'] == 0x33]
assert [x['horizontal_accuracy'] for x in criteria(a)] == [1, 1, 1]
assert [x['horizontal_accuracy'] for x in criteria(b)] == [1, 3, 3]
cases = []
for r in [a, b]:
    close = r['cleanup']
    assert r['program_exit'] == 0 and close['start_ack'] and close['stop_ack']
    assert close['client_released'] and close['device_closed'] and not close['interrupted']
    assert close['operation_mode'] == 4 and close['nmea_mask'] == 63 and close['service_revision'] == 95
    assert r['engine_states'] == [1, 2]
    assert all(x['matching_ack'] and x['ack_result'] == 0 for x in r['commands'])
    assert all(x['indication_received'] and x['indication_status'] == 0 for x in criteria(r))
    assert not r['decode_errors'] and r['taint'] == 0 and not any(r['fault_delta'].values())
    assert r['same_boot'] and r['package_database_preserved'] and r['mm_owner_and_location_properties_preserved']
    cases.append(dict(kind=r['kind'],observation_seconds_requested=90,total_native_seconds=close['elapsed_us']/1e6,
        accuracy_before_during_after=[x['horizontal_accuracy'] for x in criteria(r)],
        sv_reports=r['indication_counts']['37'],sv_reports_with_both_lists=r['sv']['ordinary_reports'],
        reports_without_either_list=r['sv']['reports_without_either_list'],
        reported_valid_snr_fields_including_both_formats=r['sv']['valid_snr'],
        positive_snr_fields=r['sv']['positive_snr'],valid_track_fields=r['sv']['valid_track'],
        snr_minimum=r['snr_minimum'],snr_maximum=r['snr_maximum'],position_status_counts=r['position_status_counts'],
        expanded_nmea_messages=r['nmea']['expanded_string_reports'],expanded_nmea_type='PQWP7',
        requested_intermediate=2,criteria_intermediate_readback=[x['intermediate'] for x in criteria(r)],
        engine_on_then_off=True,client_released_and_device_closed=True))
report = dict(stage=226,official_cases=cases,only_start_payload_difference_is_high_accuracy_tlv=True,
    same_binary_and_decoder_used=True,high_accuracy_successfully_read_back=True,
    high_accuracy_did_not_restore_positive_cnr_tracking_or_fix_under_current_conditions=True,
    firmware_reports_both_sv_lists_so_field_counts_include_duplicates=True,
    missing_lists_not_treated_as_zero_snr=True,session_id_not_returned_in_fix_session_events=True,
    requested_intermediate_not_equal_to_get_criteria_readback=True,
    post_stop_high_criteria_is_not_evidence_of_active_session=True,
    no_claim_of_fresh_aiding_validity_or_outdoor_reception=True,
    earlier_r1_r2_diagnostics_not_counted_as_official_ab=True,
    expanded_nmea_only_proven_for_vendor_debug_pqwp7_not_standard_position_sentences=True,
    current_gnss_no_fix_still_open=True,full_peripheral_goal_active=True)
(here / 'accuracy-ab-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
