#!/usr/bin/env python3
"""Summarize private stock-Android evidence without exporting positions or IDs."""
import argparse
import collections
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re


def framework(path):
    text = path.read_text()
    result = {}
    for name in ['Number of location reports', 'Number of TTFF reports',
                 'Number of CN0 reports', 'Total number of sv status messages processed',
                 'Total number of sv status messages processed, where sv is used in fix']:
        match = re.search(re.escape(name) + r':\s*(\d+)', text)
        result[name] = int(match[1]) if match else None
    gps = text.split('    gps provider:', 1)[-1].split('    network provider:', 1)[0]
    result['gps_location_present'] = bool(re.search(r'last location=Location\[gps ', gps))
    result['started'] = 'mStarted=true' in gps
    return result


def app_log(path):
    headers, counts, malformed = {}, collections.Counter(), 0
    snrs, raw_snrs, used = [], [], 0
    for line in path.read_text(errors='strict').splitlines():
        if line.startswith('#'):
            fields = next(csv.reader([line.lstrip('# ').strip()]))
            if fields and fields[0] in ('Raw', 'Status', 'Fix'):
                headers[fields[0]] = fields
            continue
        fields = next(csv.reader([line]))
        if not fields:
            continue
        kind = fields[0]
        counts[kind] += 1
        if kind in ('Raw', 'Status'):
            header = headers[kind]
            if len(fields) != len(header):
                malformed += 1
                continue
            value = float(fields[header.index('Cn0DbHz')])
            if not math.isfinite(value):
                raise ValueError('Nonfinite app C/N0')
            (snrs if kind == 'Status' else raw_snrs).append(value)
            if kind == 'Status':
                used += int(fields[header.index('UsedInFix')] == '1')
        elif kind == 'Fix':
            counts['Fix_gps_provider'] += int(fields[1] == 'gps')
        elif kind == 'NMEA' and len(fields) > 3:
            sentence = fields[1]
            if sentence.endswith('RMC'):
                counts['RMC_valid_A'] += int(fields[3] == 'A')
            elif sentence.endswith('GGA') and len(fields) > 7:
                counts['GGA_positive_fix_quality'] += int(fields[7].isdigit() and int(fields[7]) > 0)
    return dict(record_counts=dict(counts), malformed_rows=malformed,
                unknown_record_types=sorted(set(counts)-{'Raw','Status','Fix','NMEA','Nav','Fix_gps_provider','RMC_valid_A','GGA_positive_fix_quality'}),
                status_cn0_fields=len(snrs), status_positive_cn0=sum(x > 0 for x in snrs),
                status_cn0_max=max(snrs) if snrs else None, status_used_in_fix_fields=used,
                raw_cn0_fields=len(raw_snrs), raw_positive_cn0=sum(x > 0 for x in raw_snrs),
                raw_cn0_max=max(raw_snrs) if raw_snrs else None,
                forced_stop_may_leave_tail_buffer_unflushed=True)


def config_values(path):
    result = {}
    # OEM comments include non-UTF-8 punctuation; configuration keys are ASCII.
    for line in path.read_text(encoding='latin-1').splitlines():
        match = re.match(r'^\s*([A-Z_0-9]+)\s*=\s*(.*?)\s*(?:#.*)?$', line)
        if match:
            result[match[1]] = match[2]
    return result


def analyze(args):
    base = args.private_dir
    repo = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('android_decode', repo/'kernel250/decode-android-hal.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trace = base/'export/hal-stock-session.trace'
    expected = (base/'export/trace-sha256.txt').read_text().split()[0]
    assert hashlib.sha256(trace.read_bytes()).hexdigest() == expected, 'Trace transport mismatch'
    packets, parsing = module.parse_trace(trace)
    report = module.summarize(packets, parsing)
    assert not report['quality']['decode_errors']
    assert not report['measurements']['errors']
    (base/'decoded-qmi-private.json').write_text(json.dumps(packets, indent=2)+'\n')
    libraries = {}
    for line in (base/'runtime-libraries-private.txt').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        libraries[Path(name).name] = digest
    old = json.loads((repo/'kernel250/android-init-validation.json').read_text())['runtime_library_lock']
    library_matches = {name: libraries[name] == item['sha256'] for name, item in old.items()}
    vendor = config_values(base/'config-vendor-private.txt')
    odm = config_values(base/'config-odm-private.txt')
    changed = sorted(key for key in vendor.keys() & odm.keys() if vendor[key] != odm[key])
    fw_rows = {}
    for line in (base/'firmware-private.txt').read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        name = Path(path).name
        assert name not in fw_rows or fw_rows[name] == digest
        fw_rows[name] = digest
    fw_result = dict(files=len(fw_rows))
    if args.linux_firmware_manifest:
        old_fw = json.loads(args.linux_firmware_manifest.read_text())['private']['manifest']
        matches = {name: fw_rows.get(name) == item['sha256'] for name, item in old_fw.items()}
        fw_result.update(compared=len(matches), matching=sum(matches.values()),
                         all_match=all(matches.values()), missing=sum(n not in fw_rows for n in matches))
    memshare = (base/'memshare-private.txt').read_text()
    clock_start = float((base/'export/session-start-uptime.txt').read_text().split()[0])
    clock_end = float((base/'export/session-end-uptime.txt').read_text().split()[0])
    locations = {str(n): framework(base/f'export/location-{n}.txt') for n in (30, 60, 90, 120, 150, 180)}
    apps = [dict(index=i, phase='warmup' if i == 0 else 'bounded_modem_trace', **app_log(p))
            for i,p in enumerate(sorted((base/'app-logs').glob('*.txt')))]
    return dict(stage=251, environment='indoors_user_reported', android_release='11',
                stock_build='RMX1931_11_F.16', engine_observation_seconds=round(clock_end-clock_start, 2),
                trace_bytes=trace.stat().st_size, trace_sha256=expected,
                transport_sha256_verified=True, modem=report, framework=locations, app_logs=apps,
                runtime_library_matches_250=library_matches, modem_firmware=fw_result,
                configuration=dict(vendor_present=True, odm_present=True,
                    vendor_sha256=hashlib.sha256((base/'config-vendor-private.txt').read_bytes()).hexdigest(),
                    vendor_keys=len(vendor), odm_keys=len(odm), only_vendor=sorted(vendor.keys()-odm.keys()),
                    only_odm=sorted(odm.keys()-vendor.keys()), changed_keys=changed,
                    full_hal_initialization_not_captured=True),
                android_memshare=dict(client_id=1, size_bytes=5242880,
                    query_success=bool(re.search(r'query_resp\.size\s*:5242880.*query_resp\.resp\.result\s*:0',memshare)),
                    allocation_success=bool(re.search(r'alloc_resp\.num_bytes\s*: 5242880.*alloc_resp\.resp\.result\s*: 0',memshare))),
                no_nv_calibration_vendor_configuration_or_partition_write=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_dir', type=Path)
    parser.add_argument('--linux-firmware-manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ['engine_observation_seconds', 'trace_bytes',
          'transport_sha256_verified', 'runtime_library_matches_250', 'modem_firmware', 'android_memshare']}, indent=2))
