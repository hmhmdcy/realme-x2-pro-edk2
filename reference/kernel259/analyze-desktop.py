#!/usr/bin/env python3
"""Verify private exports and emit only GNSS quality/lifecycle aggregates."""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, math, struct

REFERENCE = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def bounds(values):
    values = list(values)
    assert all(math.isfinite(v) for v in values)
    return dict(samples=len(values), minimum=min(values) if values else None,
                maximum=max(values) if values else None)


def analyze(rows):
    decoder = module('decoder246', REFERENCE/'kernel246/loc_decode.py')
    raw = module('measurements254', REFERENCE/'kernel254/analyze-qmi-measurements.py')
    rf = module('radio255', REFERENCE/'kernel255/analyze-pga-clock.py')
    quality = decoder.summarize(rows)
    radio, _details = rf.analyze(rows)
    packets = [dict(**r, flags=4, time=r['elapsed_us']/1e6)
               for r in rows if r.get('kind') == 'indication']
    _measurements, records = raw.analyze(packets)
    gps, positions, technology = [], [], collections.Counter()
    for row in packets:
        tlvs = row['tlvs']
        if row['message_id'] == 0x25 and '16' in tlvs:
            data = bytes.fromhex(tlvs['16'])
            decoder.sv_list(data)
            satellites = [struct.unpack_from('<IIHBIBfff', data, 1+28*i)
                          for i in range(data[0])]
            satellites = [v for v in satellites if v[0] & 1 and v[1] == 1]
            gps.append(dict(unique_track=len({v[2] for v in satellites
                                             if v[0] & 8 and v[4] == 3}),
                            cn0=[v[8] for v in satellites
                                 if v[0] & 128 and math.isfinite(v[8]) and v[8] > 0]))
        if (row['message_id'] == 0x24 and decoder.uint(tlvs, 1, 4) == 0
                and all(k in tlvs and len(bytes.fromhex(tlvs[k])) == 8
                        for k in ('16', '17'))):
            latitude, longitude = (struct.unpack('<d', bytes.fromhex(tlvs[k]))[0]
                                   for k in ('16', '17'))
            if (math.isfinite(latitude) and math.isfinite(longitude)
                    and -90 <= latitude <= 90 and -180 <= longitude <= 180):
                positions.append(row['time'])
                technology[str(decoder.uint(tlvs, 35, 4))] += 1
    fresh = [v['host_time'] for v in records if v['system'] == 1
             and v['valid_status'] & 0x08000000 and v['measurement_status'] & 0x08000000]
    return dict(indication_counts=quality['indication_counts'],
                position_status_counts=quality['position_status_counts'],
                valid_positions=len(positions),
                first_valid_seconds=positions[0] if positions else None,
                continuous_position_span_seconds=positions[-1]-positions[0] if positions else 0,
                position_technology_masks=dict(technology), nmea=quality['nmea'],
                gps_unique_track_per_report=bounds(v['unique_track'] for v in gps),
                gps_positive_cn0_dbhz=bounds(c for v in gps for c in v['cn0']),
                gps_raw_status_counts=dict(collections.Counter(v['status'] for v in records if v['system'] == 1)),
                gps_fresh_records=len(fresh),
                gps_fresh_span_seconds=max(fresh)-min(fresh) if fresh else 0,
                pga_counts=radio['pga_counts'], pga_not_observed_is_not_zero=True,
                clock_source_counts=radio['clock_source_counts'],
                clock_reset_counts=radio['num_clock_resets_counts'],
                clock_uncertainty_mps=radio['clock_drift_uncertainty_mps'],
                commands=quality['commands'],
                cleanup=[r for r in rows if r['kind'] in ['cleanup', 'report_cleanup']],
                decode_errors=quality['decode_errors'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_directory', type=Path)
    parser.add_argument('--output-directory', required=True, type=Path)
    args = parser.parse_args()
    private = args.private_directory
    manifest = json.loads((private/'retrieval-manifest-private.json').read_text())
    for entry in manifest:
        data = (private/'retrieved'/entry['name']).read_bytes()
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
    report = dict(stage=259, exports_sha_verified=len(manifest),
                  compressed_export_bytes=(private/'retrieval-private.zip').stat().st_size)
    for label, filename in [('native_high', 'native-high-control/events-private.jsonl'),
                            ('observer', 'outdoor-r1/observer-events-private.jsonl')]:
        rows = [json.loads(v) for v in (private/'retrieved'/filename).read_text().splitlines()]
        report[label] = analyze(rows)
        if label == 'observer':
            # A conservative prefix is entirely before the overlapping HIGH client.
            report['observer_first_240_seconds'] = analyze(
                [v for v in rows if v.get('elapsed_us', 0) < 240e6])
    states = {}
    for label, filename in [('baseline', 'baseline/progress.json'),
                            ('candidate', 'candidate-r1/progress.json'),
                            ('outdoor', 'outdoor-r1/progress.json')]:
        value = json.loads((private/'retrieved'/filename).read_text())
        states[label] = {k: value[k] for k in ['phase', 'rounds', 'old_signals', 'old_refresh',
                         'old_power', 'final_without_normalization', 'desktop_setting_restored',
                         'base_config_unchanged', 'location_settings_restored_without_manual_normalization',
                         'power_unchanged', 'taint', 'elapsed_seconds'] if k in value}
    high = json.loads((private/'retrieved/native-high-control/state.json').read_text())
    report['high_control'] = {k: high[k] for k in ['phase', 'outdoor_elapsed_at_start',
                              'accuracy', 'duration_seconds', 'normal_modem_power_unchanged',
                              'returncode']}
    report['power_comparison'] = dict(normal_online_request_rejected=True,
                                      online_phase_not_reached=True,
                                      original_offline_state_restored=True)
    report['limitations'] = dict(desktop_fix_not_verified=True,
                                high_request_accepted_but_no_fix_in_offline_state=True,
                                standard_only_prefix_seconds=240,
                                high_client_overlaps_final_desktop_seconds=True,
                                clock_reset_counter_stable_during_observation=True,
                                rf_gain_or_clock_root_cause_not_identified=True)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    (args.output_directory/'summary-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    (args.output_directory/'lifecycle-validation.json').write_text(json.dumps(states, indent=2)+'\n')
    print(json.dumps(dict(exports_verified=len(manifest),
                         outdoor_desktop_locations=states['outdoor']['rounds'][0]['valid_location_events'],
                         native_high_locations=report['native_high']['valid_positions'],
                         candidate_preferences_restored=states['candidate']['location_settings_restored_without_manual_normalization'])))


if __name__ == '__main__':
    main()
