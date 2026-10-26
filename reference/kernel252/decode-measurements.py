#!/usr/bin/env python3
"""Summarize GNSS v0 measurements using the layouts locked in stage 247.

Input is private logs-private.json from decode-diag-trace.py. Never treats
missing SV records as zero C/N0. No coordinates or satellite IDs in output.
"""
import argparse
import collections
import json
import math
from pathlib import Path
import struct


def summarize(logs):
    reference = Path(__file__).resolve().parents[1]
    layouts = json.loads((reference / 'kernel247/comparison-online-satellite-validation.json').read_text())['layouts']
    systems = {}
    for name, code, fmt in [('GPS', 0x1477, '<BIHIffffB'),
                            ('GLONASS', 0x1480, '<BIBHIffffB'),
                            ('GALILEO', 0x1886, '<BBBIHIffffB')]:
        schema = layouts[name]
        hs, stride = schema['header_bytes'], schema['sv_stride']
        assert hs == struct.calcsize(fmt)
        reports = []
        for row in logs:
            if row['code'] != code:
                continue
            body = bytes.fromhex(row['payload_hex'])[16:]
            if len(body) < hs or body[0] != 0:
                raise ValueError('Unsupported measurement version or short header')
            count = body[hs - 1]
            if len(body) != hs + count * stride:
                raise ValueError('Measurement count/stride mismatch')
            clock = struct.unpack_from(fmt, body)[-5:-1]
            if not all(math.isfinite(value) for value in clock):
                raise ValueError('Nonfinite measurement clock fields')
            satellites = []
            for i in range(count):
                record = body[hs + i * stride:hs + (i + 1) * stride]
                cn0 = struct.unpack_from('<H', record, schema['cno_offset'])[0]
                status = schema['measurement_status_offset']
                satellites.append(dict(cn0=cn0, obs=record[schema['obs_state_offset']],
                                       status=record[status:status + 4].hex()))
            reports.append(dict(records=count, clock=clock, satellites=satellites))
        satellites = [s for r in reports for s in r['satellites']]
        systems[name] = dict(reports=len(reports),
            record_count_distribution=dict(collections.Counter(r['records'] for r in reports)),
            cno_fields=len(satellites), positive_cno=sum(s['cn0'] > 0 for s in satellites),
            max_cno_dbhz=max((s['cn0'] / 100 for s in satellites), default=None),
            obs_state_raw_counts=dict(collections.Counter(s['obs'] for s in satellites)),
            measurement_status_raw_counts=dict(collections.Counter(s['status'] for s in satellites)),
            clock_ranges={key: dict(min=min(r['clock'][i] for r in reports),
                                    max=max(r['clock'][i] for r in reports))
                          for i, key in enumerate(['time_bias', 'time_unc', 'clock_freq_bias', 'clock_freq_unc'])}
                         if reports else {})
    shapes = {}
    for code in sorted({r['code'] for r in logs}):
        bodies = [bytes.fromhex(r['payload_hex'])[16:] for r in logs if r['code'] == code]
        shapes[hex(code)] = dict(reports=len(bodies),
            body_lengths=dict(collections.Counter(len(b) for b in bodies)),
            first_byte_counts=dict(collections.Counter(b[0] for b in bodies)))
    return dict(systems=systems, shapes=shapes, layouts=layouts,
                strict_version_and_stride=True, clock_float_units_not_assumed=True,
                missing_records_not_zero_cn0=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_logs', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.private_logs.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: {field: value[field] for field in ['reports', 'cno_fields', 'positive_cno']}
                      for k, value in result['systems'].items()}))


if __name__ == '__main__':
    main()
