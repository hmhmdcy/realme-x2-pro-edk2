#!/usr/bin/env python3
"""Read-only sanitized summaries for nonoverlapping phases of one HAL trace.

The phase JSON is [{"name": ..., "start": epoch_seconds, "end": ...}, ...].
Raw trace and phase timestamps remain private. This refuses a closed/reused
LOC fd and identifies the socket from actual register-events requests.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re


def analyze(trace, phases):
    spec = importlib.util.spec_from_file_location('decoder',
        Path(__file__).resolve().parents[1] / 'kernel250/decode-android-hal.py')
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    packets, parsing = decoder.parse_trace(trace)
    full = decoder.summarize(packets, parsing)
    fds = full['loc_socket_fds']
    text = trace.read_text()
    if any(re.search(r'close\(' + str(fd) + r'(?:<[^\n]*>)?\)\s+=\s+0', text) for fd in fds):
        raise ValueError('LOC fd closed; phase split would need independent re-identification')
    names, previous_end, result = set(), -math.inf, {}
    for phase in phases:
        name, start, end = phase['name'], phase['start'], phase['end']
        if name in names or not all(math.isfinite(x) for x in [start, end]) or not previous_end <= start < end:
            raise ValueError('Duplicate, invalid or overlapping phase')
        names.add(name)
        previous_end = end
        subset = [p for p in packets if start <= p['time'] < end]
        report = decoder.summarize(subset, {}, fds)
        if report['quality']['decode_errors'] or report['measurements']['errors']:
            raise ValueError('Invalid decoded phase')
        result[name] = dict(duration_seconds=end - start, report=report)
    return dict(parsing=parsing, phases=result,
                socket_continuity_checked=True, raw_payload_or_satellite_ids_not_exported=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_trace', type=Path)
    parser.add_argument('private_phases_json', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.private_trace, json.loads(args.private_phases_json.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({name: dict(seconds=row['duration_seconds'],
        sv_reports=row['report']['quality']['sv'].get('ordinary_reports', 0),
        positive_status_fields=row['report']['quality']['sv'].get('positive_snr', 0),
        successful_positions=row['report']['quality']['successful_qmi_positions_with_valid_coordinates'])
        for name, row in result['phases'].items()}))


if __name__ == '__main__':
    main()
