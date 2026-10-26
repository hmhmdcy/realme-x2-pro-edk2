"""Inspect strict v0 GPS records without exporting satellite IDs or payloads.

The field positions and float conversion follow the SHA-locked MobileInsight
GPS layout already used in stage 247. Status bits and float units are not
invented. Positive C/N0 is not treated as a usable pseudorange.
"""
from pathlib import Path
import collections
import hashlib
import json
import math
import struct

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path('/mnt/e/edk2-samurai-out')


def distribution(values):
    values = list(values)
    finite = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    counter = collections.Counter(values)
    return dict(samples=len(values), finite_samples=len(finite),
                min=min(finite) if finite else None,
                max=max(finite) if finite else None,
                zero_samples=sum(v == 0 for v in values),
                distinct=len(counter))


def decode(logs):
    reports = []
    for log in logs:
        if log['code'] != 0x1477:
            continue
        packet = bytes.fromhex(log['payload_hex'])
        body = packet[16:]
        if len(body) < 28 or body[0] != 0 or len(body) != 28 + 70 * body[27]:
            raise ValueError('Unsupported GPS layout')
        version, fcount, week, ms, bias, tunc, fbias, func, count = struct.unpack_from('<BIHIffffB', body)
        satellites = []
        for i in range(count):
            record = body[28 + 70*i:28 + 70*(i+1)]
            floats = {key: struct.unpack_from('<f', record, offset)[0]
                      for key, offset in [('sub_ms', 18), ('time_unc', 22),
                                          ('speed', 26), ('speed_unc', 30),
                                          ('fine_speed', 57), ('fine_speed_unc', 61)]}
            satellites.append(dict(sv=record[0], obs=record[1],
                cno=struct.unpack_from('<H', record, 7)[0] / 100,
                tot=record[2], gd=record[3], parity=record[4:6].hex(), filt_n=record[6],
                latency=struct.unpack_from('<h', record, 9)[0], pre=record[11],
                post=struct.unpack_from('<H', record, 12)[0],
                ms=struct.unpack_from('<I', record, 14)[0],
                measurement_status=record[34:38].hex(), misc_status=record[38],
                carrier_phase_integer=struct.unpack_from('<I', record, 51)[0],
                carrier_phase_fraction=struct.unpack_from('<H', record, 55)[0],
                cycle_slip=record[65], **floats))
        reports.append(dict(fcount=fcount, week=week, ms=ms, time_bias=bias,
                            time_unc=tunc, freq_bias=fbias, freq_unc=func,
                            diag_timestamp=struct.unpack_from('<Q', packet, 8)[0],
                            satellites=satellites))
    return reports


def summarize_records(records):
    fields = ['cno', 'tot', 'gd', 'filt_n', 'latency', 'pre', 'post', 'ms',
              'sub_ms', 'time_unc', 'speed', 'speed_unc', 'fine_speed',
              'fine_speed_unc', 'carrier_phase_integer',
              'carrier_phase_fraction', 'cycle_slip', 'misc_status']
    return dict(records=len(records),
                observation_state_counts=dict(collections.Counter(r['obs'] for r in records)),
                measurement_status_byte_counts=dict(collections.Counter(r['measurement_status'] for r in records)),
                parity_byte_counts=dict(collections.Counter(r['parity'] for r in records)),
                fields={key: distribution(r[key] for r in records) for key in fields})


def main():
    source = PRIVATE / 'kernel244/gnss-layouts/gnss_gps_measurement_report.h'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == '3761ff87f09b9329b9ccde8efcd448ceb40e562952849e65d59b11da978da24d'
    paths = {
        'stock253_abab': PRIVATE/'kernel253/diag-abab-enabled-decoded/logs-private.json',
        'linux247_baseline': PRIVATE/'kernel247/baseline-off-decoded-log-envelopes-private.json',
        'linux247_online': PRIVATE/'kernel247/comparison-online-decoded-log-envelopes-private.json',
    }
    report = dict(layout_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), groups={})
    private = {}
    for name, path in paths.items():
        rows = decode(json.loads(path.read_text()))
        private[name] = rows
        records = [sv for r in rows for sv in r['satellites']]
        positive = [sv for sv in records if sv['cno'] > 0]
        zero = [sv for sv in records if sv['cno'] == 0]
        positive_ids = {sv['sv'] for sv in positive}
        same_sv_zero = [sv for sv in zero if sv['sv'] in positive_ids]
        positive_reports = [r for r in rows if any(sv['cno'] > 0 for sv in r['satellites'])]
        report['groups'][name] = dict(reports=len(rows),
            positive=summarize_records(positive), zero=summarize_records(zero),
            same_positive_id_zero=summarize_records(same_sv_zero),
            positive_id_count=len(positive_ids),
            clock={key: distribution(r[key] for r in rows)
                   for key in ['time_bias', 'time_unc', 'freq_bias', 'freq_unc']},
            positive_clock={key: distribution(r[key] for r in positive_reports)
                   for key in ['time_bias', 'time_unc', 'freq_bias', 'freq_unc']},
            report_time_step_counts=dict(collections.Counter(b['ms']-a['ms'] for a,b in zip(rows,rows[1:]))))
    report.update(raw_status_bits_not_interpreted=True,
                  speed_and_time_uncertainty_units_not_assumed=True,
                  positive_cno_not_assumed_usable_measurement=True)
    (PRIVATE/'kernel254/search-measurements-private.json').write_text(json.dumps(private, indent=2, allow_nan=False)+'\n')
    (ROOT/'kernel254/search-measurements-validation.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({name:dict(reports=g['reports'], positive=g['positive'],
                               positive_clock=g['positive_clock'], clock=g['clock'])
                      for name,g in report['groups'].items()}, indent=2))


if __name__ == '__main__':
    main()
