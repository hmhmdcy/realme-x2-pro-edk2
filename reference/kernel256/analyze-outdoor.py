#!/usr/bin/env python3
"""Summarize private outdoor LOC captures without publishing positions or IDs."""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def ranges(values):
    values = list(values)
    assert all(math.isfinite(v) for v in values)
    return dict(samples=len(values), minimum=min(values) if values else None,
                maximum=max(values) if values else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_directory', type=Path)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    private, output = args.private_directory, args.output_directory
    output.mkdir(exist_ok=True, parents=True)
    receipt = json.loads((private / 'outdoor-export-manifest-private.json').read_text())
    for entry in receipt:
        data = (private / entry['name']).read_bytes()
        assert len(data) == entry['bytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
    wire = module('wire250', ROOT / 'kernel250/decode-android-hal.py')
    rf = module('rf255', ROOT / 'kernel255/analyze-pga-clock.py')
    measurements = module('measurement254', ROOT / 'kernel254/analyze-qmi-measurements.py')
    packets, parsing = wire.parse_trace(private / 'hal-outdoor.trace')
    quality = wire.summarize(packets, parsing)
    fds = set(quality['loc_socket_fds'])
    loc = [p for p in packets if p['fd'] in fds]
    indications = [p for p in loc if p['direction'] == 'recv' and p['flags'] == 4]
    radio, _ = rf.analyze(loc)
    raw, rows = measurements.analyze(indications)
    positions, uncertainties, confidences, statuses = [], [], [], collections.Counter()
    technology = collections.Counter()
    nonzero_status = []
    origin = min(p['time'] for p in loc)
    for row in indications:
        if row['message_id'] != 0x24:
            continue
        tlvs = row['tlvs']
        status = struct.unpack('<I', bytes.fromhex(tlvs['1']))[0]
        statuses[status] += 1
        if status:
            nonzero_status.append(dict(seconds_from_capture_first_packet=row['time']-origin, status=status))
            continue
        lat, lon = (bytes.fromhex(tlvs.get(str(t), '')) for t in (16, 17))
        if len(lat) != 8 or len(lon) != 8:
            continue
        lat, lon = struct.unpack('<d', lat)[0], struct.unpack('<d', lon)[0]
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        positions.append(row['time'])
        if '35' in tlvs:
            b = bytes.fromhex(tlvs['35']); assert len(b) == 4
            technology[struct.unpack('<I', b)[0]] += 1
        if '18' in tlvs:
            b = bytes.fromhex(tlvs['18']); assert len(b) == 4
            uncertainties.append(struct.unpack('<f', b)[0])
        if '22' in tlvs:
            b = bytes.fromhex(tlvs['22']); assert len(b) == 1
            confidences.append(b[0])
    gaps = [b-a for a,b in zip(positions, positions[1:])]
    ordinary = []
    decoder = module('quality246', ROOT / 'kernel246/loc_decode.py')
    for row in indications:
        if row['message_id'] != 0x25 or '16' not in row['tlvs']:
            continue
        data = bytes.fromhex(row['tlvs']['16'])
        decoder.sv_list(data)
        gps = dict(time=row['time'], track=0, unique_track=0, positive=0, cn0=[])
        tracked_ids = set()
        for i in range(data[0]):
            mask, system, sv_id, _, status, _, _, _, cn0 = struct.unpack_from('<IIHBIBfff', data, 1+28*i)
            if system != 1 or not mask & 1:
                continue
            gps['track'] += int(bool(mask & 8) and status == 3)
            if mask & 8 and status == 3:
                tracked_ids.add(sv_id)
            if mask & 128 and math.isfinite(cn0) and cn0 > 0:
                gps['positive'] += 1; gps['cn0'].append(cn0)
        gps['unique_track'] = len(tracked_ids)
        ordinary.append(gps)
    per_system = {}
    for system in sorted({r['system'] for r in rows}):
        subset = [r for r in rows if r['system'] == system]
        epochs = collections.defaultdict(list)
        for r in subset:
            epochs[r['host_time']].append(r)
        fresh = [t for t, values in epochs.items() if any(
            r['valid_status'] & 0x08000000 and r['measurement_status'] & 0x08000000 for r in values)]
        per_system[str(system)] = dict(records=len(subset), measurement_reports=len(epochs),
            reports_with_fresh=len(fresh), fresh_report_span_seconds=fresh[-1]-fresh[0] if fresh else 0,
            status_counts=dict(collections.Counter(r['status'] for r in subset)),
            validity={name:dict(valid=sum(bool(r['valid_status'] & bit) for r in subset),
                true_when_valid=sum(bool(r['valid_status'] & bit and r['measurement_status'] & bit) for r in subset))
                for name, bit in measurements.FLAGS.items()},
            cno_dbhz=ranges(r['cno'] for r in subset))
    summary = dict(stage=256, user_confirmed_outdoors_and_usb_disconnected=True,
        wireless_transport=True, same_stock_boot_and_hal_as_255=True,
        source_exports_sha_verified=len(receipt),
        loc_socket_identified_by_current_register_events_request=True,
        valid_coordinate_position_reports=len(positions), position_status_counts=dict(statuses),
        nonzero_position_status_events=nonzero_status,
        position_technology_mask_counts={hex(k):v for k,v in technology.items()},
        satellite_used_reports=sum(v for k,v in technology.items() if k & 1),
        propagated_position_reports=sum(v for k,v in technology.items() if k & 0x800),
        continuous_position_span_seconds=positions[-1]-positions[0] if positions else 0,
        position_gap_seconds=ranges(gaps),
        reported_horizontal_uncertainty_circular_m=ranges(uncertainties),
        reported_horizontal_confidence_counts=dict(collections.Counter(confidences)),
        reported_uncertainty_is_not_surveyed_absolute_accuracy=True,
        gps_ordinary_reports=len(ordinary), gps_track_per_report=ranges(r['track'] for r in ordinary),
        gps_track_per_report_is_entry_count_not_unique_satellites=True,
        gps_unique_track_per_report=dict(reports=len(ordinary),track_entries_min=min(r['track'] for r in ordinary),track_entries_max=max(r['track'] for r in ordinary),
            unique_track_min=min(r['unique_track'] for r in ordinary),unique_track_max=max(r['unique_track'] for r in ordinary),unique_track_last=ordinary[-1]['unique_track'],
            duplicate_track_entries=sum(r['track']-r['unique_track'] for r in ordinary)),
        unique_satellite_count_audited_at_stage=258,
        gps_positive_cn0_per_report=ranges(r['positive'] for r in ordinary),
        gps_cn0_dbhz=ranges(v for r in ordinary for v in r['cn0']),
        gps_latest_ordinary_report={k:v for k,v in ordinary[-1].items() if k != 'time'} if ordinary else None,
        pga_counts=radio['pga_counts'], clock_source_counts=radio['clock_source_counts'],
        clock_drift_uncertainty_mps=radio['clock_drift_uncertainty_mps'],
        num_clock_resets_counts=radio['num_clock_resets_counts'],
        raw_measurements_by_system=per_system,
        cold_start_ttff_not_measured=True,
        outdoor_and_usb_disconnect_are_confounded_changes=True,
        linux_not_retested_outdoors_this_stage=True,
        pga_change_is_observation_not_identified_cause=True)
    for name, value in [('quality-validation.json', quality), ('pga-clock-validation.json', radio),
                        ('measurements-validation.json', raw), ('summary-validation.json', summary)]:
        (output / name).write_text(json.dumps(value, indent=2)+'\n')
    (private / 'decoded-qmi-private.json').write_text(json.dumps(packets)+'\n')
    (private / 'decoded-measurements-private.json').write_text(json.dumps(rows)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
