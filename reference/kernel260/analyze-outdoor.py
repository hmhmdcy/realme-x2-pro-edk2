#!/usr/bin/env python3
"""Verify private field exports and publish coordinate-free GNSS aggregates."""
from pathlib import Path
import argparse
import collections
import hashlib
import importlib.util
import json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_directory', type=Path)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    private, output = args.private_directory, args.output_directory
    directory = private/'field-retrieved'
    manifest = json.loads((private/'field-retrieval-manifest-private.json').read_text())
    for entry in manifest:
        path = (directory/entry['name']).resolve()
        assert path.is_relative_to(directory.resolve())
        data = path.read_bytes()
        assert len(data) == entry['bytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
    state = json.loads((directory/'outdoor-policy/progress.json').read_text())
    retrieval = json.loads((directory/'field-retrieval-state-private.json').read_text())
    assert state['phase'] == 'complete' and len(state['rounds']) == 1
    client = state['rounds'][0]
    assert client['uid'] == 10000 and client['returncode'] == 0
    assert all(client[k] for k in ['started', 'stopped', 'client_deleted', 'active'])
    times = client['event_elapsed_seconds']
    assert len(times) == client['valid_location_events'] == client['fresh_timestamp_events']
    assert times == sorted(times) and len(set(times)) == len(times)
    assert client['location_events'] >= len(times) > 0
    assert state['location_settings_restored_without_manual_normalization']
    assert state['desktop_setting_restored'] and state['base_config_unchanged']
    assert state['last']['power'] == 2 and not state['power_policy']['owned']
    assert state['taint'] == 0 and state['observer_returncode'] == 0
    assert retrieval['awake']['held'] and retrieval['awake']['released']
    assert not retrieval['field_worker_process_present']
    source = Path(__file__).resolve().parents[1]/'kernel259/analyze-desktop.py'
    spec = importlib.util.spec_from_file_location('field_decoder259', source)
    analyzer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analyzer)
    rows = [json.loads(v) for v in
            (directory/'outdoor-policy/observer-events-private.jsonl').read_text().splitlines()]
    quality = analyzer.analyze(rows)
    assert quality['decode_errors'] == []
    samples = [json.loads(v) for v in
               (directory/'outdoor-policy/samples-private.jsonl').read_text().splitlines()]
    report = dict(
        stage=260, exports_sha_verified=len(manifest),
        compressed_export_bytes=(private/'field-retrieval-private.zip').stat().st_size,
        desktop=dict(
            uid=client['uid'], requested_duration_seconds=300,
            client_elapsed_seconds=client['elapsed_seconds'],
            location_updated_events=client['location_events'],
            conservative_positive_accuracy_validated_events=len(times),
            recent_changed_timestamp_events=client['fresh_timestamp_events'],
            unclassified_events_with_old_collector=client['location_events']-len(times),
            first_validated_event_seconds=times[0],
            last_validated_event_seconds=times[-1],
            validated_event_span_seconds=times[-1]-times[0],
            first_240_seconds_validated_max_gap_seconds=max(
                b-a for a, b in zip(times, times[1:]) if b <= 240),
            start_stop_delete_succeeded=True,
            gnss_only_source_configuration=True,
            additional_native_high_client=False,
            standard_mm_horizontal_accuracy_default='LOW'),
        satellite_observer={k: quality[k] for k in [
            'gps_unique_track_per_report', 'gps_positive_cn0_dbhz',
            'gps_raw_status_counts', 'gps_fresh_records', 'gps_fresh_span_seconds',
            'pga_counts', 'pga_not_observed_is_not_zero', 'clock_source_counts',
            'clock_reset_counts', 'clock_uncertainty_mps', 'decode_errors']},
        power=dict(sample_counts=dict(collections.Counter(str(v['power']) for v in samples)),
                   final_mm_power=2, online_requests_this_field_run=1,
                   low_power_releases_this_field_run=1, owned_lease_remaining=False),
        cleanup=dict(final_gps_settings=state['final_without_normalization'],
                     desktop_privacy_setting_restored=True,
                     geoclue_configuration_unchanged=True,
                     settings_restored_without_manual_normalization=True,
                     original_wifi_power_save_restored=True,
                     temporary_session_inhibitor_released=True,
                     observer_returncode=0, field_worker_remaining=False, taint=0),
        environment=dict(usb_unplugged_for_field_run=True,
                         suspend_success_count=retrieval['suspend_success'],
                         estimated_suspended_seconds=retrieval['total_suspend_seconds_estimate'],
                         helper_time_prepared=retrieval['helper']['time_prepared']),
        limitations=dict(
            old_collector_required_accuracy_strictly_positive=True,
            upstream_hdop_mapping_can_return_zero_accuracy=True,
            zero_reported_accuracy_is_not_proven_zero_physical_error=True,
            rejected_event_fields_not_recorded=True,
            fresh_timestamp_count_compares_each_timestamp_to_previous_event=True,
            all_18_rejections_cannot_be_assumed_zero_accuracy=True,
            strict_subset_gaps_do_not_prove_radio_fix_loss=True,
            first_event_is_not_a_cold_start_ttff=True,
            observer_had_no_own_position_session=True,
            observer_zero_position_indications_do_not_negate_desktop_fixes=True,
            pga_not_observed_in_this_capture=True,
            rf_clock_initialization_equivalence_not_proven=True,
            cold_start_suspend_long_stability_absolute_accuracy_unverified=True))
    output.mkdir(parents=True, exist_ok=True)
    (output/'outdoor-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(exports_verified=len(manifest),
                          desktop_events=client['location_events'],
                          conservative_fresh_events=len(times),
                          max_unique_gps_track=quality['gps_unique_track_per_report']['maximum'],
                          max_cn0_dbhz=quality['gps_positive_cn0_dbhz']['maximum'],
                          final_mm_power=2)))


if __name__ == '__main__':
    main()
