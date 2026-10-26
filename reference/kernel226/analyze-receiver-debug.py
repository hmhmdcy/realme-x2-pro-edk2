"""Offline aiding/RF summaries; never export PQWP2 coordinates or raw NMEA."""
from pathlib import Path
import base64
import collections
import hashlib
import importlib.util
import json
import tarfile
import urllib.request
from loc_decode import nmea_text

here = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel226')
old = private.parent / 'kernel208/receiver-sources'
source_proof = json.loads((here.parent / 'kernel208/receiver-source-validation.json').read_text())
for original, record in source_proof['files'].items():
    assert hashlib.sha256((old / original.replace('/', '__')).read_bytes()).hexdigest() == record['sha256']
commit = source_proof['official_pinned_commit']
url = 'https://android.googlesource.com/platform/hardware/qcom/sm8150/gps/+/' + commit + '/location/LocationDataTypes.h?format=TEXT'
target = private / 'qualcomm-loc-public-sources/LocationDataTypes.h'
if target.exists():
    header = target.read_bytes()
else:
    header = base64.b64decode(urllib.request.urlopen(url, timeout=30).read())
    target.write_bytes(header)
text = header.decode()
assert 'GNSS_EPH_TYPE_UNKNOWN = 0,' in text
assert 'GNSS_EPH_SOURCE_UNKNOWN = 0,' in text
spec = importlib.util.spec_from_file_location('pqwm208', here.parent / 'kernel208/pqwm1.py')
pq = importlib.util.module_from_spec(spec); spec.loader.exec_module(pq)
assert pq.selftest()['missing_and_nan_not_zero']
groups = [('gps', 32), ('glonass', 24), ('qzss', 5), ('beidou', 37), ('galileo', 36), ('navic', 14)]
aid_groups = ['gps', 'glonass', 'beidou', 'galileo', 'qzss']
def bounds(values):
    available = [v for v in values if v is not None]
    return dict(min=min(available) if available else None, max=max(available) if available else None, samples=len(available))
out = []
with tarfile.open(private / 'final-evidence-private.tar.gz') as archive:
    for case in ['default', 'high']:
        member = 'k226-loc-r3-' + case + '/events-private.jsonl'
        rows = [json.loads(l) for l in archive.extractfile(member).read().splitlines()]
        m1, p3, p4, p7, errors = [], [], [], [], []
        for row in rows:
            if row['kind'] != 'indication' or row['message_id'] != 0x26:
                continue
            tlvs = row['tlvs']
            raw = bytes.fromhex(tlvs.get('16') or tlvs.get('1') or '')
            if not raw:
                continue
            for sentence in nmea_text(raw).replace('\r', '').split('\n'):
                if not sentence:
                    continue
                try:
                    f = pq.sentence(sentence)
                    if f[0] == 'PQWM1':
                        m1.append(pq.decode(sentence))
                    elif f[0] == 'PQWP3':
                        if len(f) < 13:
                            raise ValueError('short P3')
                        p3.append(dict(mask=int(f[2], 16) if f[2] else None,
                                       ages=[int(v, 10) if v else None for v in f[3:8]],
                                       valid_counts=[int(v, 16).bit_count() if v else None for v in f[8:13]]))
                    elif f[0] == 'PQWP4':
                        if len(f) < 7:
                            raise ValueError('short P4')
                        p4.append([int(v, 16).bit_count() for v in f[2:7]])
                    elif f[0] == 'PQWP7':
                        n = (len(f) - 2) // 3
                        if len(f) != 2 + 3 * n or n not in [134, 148]:
                            raise ValueError('unverified P7 slot count')
                        values = [tuple(int(v, 10) if v else None for v in f[2+3*i:5+3*i]) for i in range(n)]
                        p7.append(values)
                except ValueError:
                    errors.append(dict(type=sentence.split(',', 1)[0][:8], error='format_or_checksum'))
        summary = dict(case=case, pqwm1_reports=len(m1), pqwp3_reports=len(p3),
                       pqwp4_reports=len(p4), expanded_pqwp7_reports=len(p7), decode_errors=errors)
        names = ['time_valid','time_source','time_unc','clock_bias','clock_bias_unc','xo_state','pga_gain',
                 'adc_i','adc_q','jammer_gps','jammer_glo','jammer_bds','jammer_gal','error_recovery',
                 'agc_gps','agc_glo','agc_bds','agc_gal']
        summary['clock_rf_ranges'] = {name: dict(min=min(v),max=max(v),samples=len(v)) for name in names
                                      if (v := [x[name] for x in m1 if x[name] is not None])}
        if p3:
            summary['xtra_reported_masks'] = dict(collections.Counter(str(x['mask']) for x in p3))
            summary['xtra_age_and_valid_count_ranges'] = {
                aid_groups[i]: dict(age=bounds([x['ages'][i] for x in p3]),
                                   valid_count=bounds([x['valid_counts'][i] for x in p3]))
                for i in range(5)}
        if p4:
            summary['ephemeris_valid_count_ranges'] = {aid_groups[i]:dict(min=min(x[i] for x in p4),max=max(x[i] for x in p4)) for i in range(5)}
        if p7:
            summary['nav_slot_counts'] = sorted({len(x) for x in p7})
            summary['nav_by_constellation'] = {}
            offset = 0
            for name, count in groups:
                samples = [x[offset:offset+count] for x in p7 if len(x) >= offset+count]
                offset += count
                if not samples:
                    continue
                summary['nav_by_constellation'][name] = dict(
                    ephemeris_count_min=min(sum(v[0] == 1 for v in x) for x in samples),
                    ephemeris_count_max=max(sum(v[0] == 1 for v in x) for x in samples),
                    almanac_count_min=min(sum(v[0] == 2 for v in x) for x in samples),
                    almanac_count_max=max(sum(v[0] == 2 for v in x) for x in samples),
                    missing_type_count_min=min(sum(v[0] is None for v in x) for x in samples),
                    missing_type_count_max=max(sum(v[0] is None for v in x) for x in samples),
                    source_counts=dict(collections.Counter('missing' if v[1] is None else str(v[1]) for x in samples for v in x)))
        out.append(summary)
report = dict(stage=226,cases=out,offline_from_verified_private_archive=True,
    public_sm8150_parser_commit=commit,additional_enum_source=dict(url=url,sha256=hashlib.sha256(header).hexdigest()),
    ephemeris_type_enum=dict(unknown=0,ephemeris=1,almanac=2),
    ephemeris_source_enum=dict(unknown=0,demodulated=1,supl=2,other_server=3,local=4),
    coordinates_satellite_identifiers_and_raw_nmea_not_exported=True,
    empty_optional_values_preserved_as_missing_not_zero=True,
    firmware_debug_telemetry_is_not_rf_hardware_or_optical_proof=True)
assert not any(case['decode_errors'] for case in out)
(here / 'receiver-debug-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
