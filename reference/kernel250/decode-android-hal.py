#!/usr/bin/env python3
"""Decode strace -f -ttt -xx LOC datagrams; raw exports remain private.

Run against an unmodified trace copied from the handset. This does not connect
to a device, send QMI commands, or export positions in the summary.
"""
import argparse
import collections
import importlib.util
import json
import math
from pathlib import Path
import re
import struct

LINE = re.compile(r'^(\d+)\s+(\d+\.\d+)\s+(.*)$')
HEX = re.compile(r'"((?:\\x[0-9a-fA-F]{2})+)"')


def decode_wire(raw):
    offsets = [0]
    if len(raw) >= 13 and raw[0] == 1 and int.from_bytes(raw[1:3], 'little') == len(raw) - 1:
        offsets.append(6)
    for offset in offsets:
        wire = raw[offset:]
        if len(wire) < 7 or wire[0] not in (0, 2, 4):
            continue
        transaction, ident, size = struct.unpack_from('<HHH', wire, 1)
        if size + 7 != len(wire):
            continue
        tlvs, pos = {}, 7
        while pos < len(wire):
            if pos + 3 > len(wire):
                raise ValueError('Truncated QMI TLV header')
            tag, length = struct.unpack_from('<BH', wire, pos)
            pos += 3
            if pos + length > len(wire) or str(tag) in tlvs:
                raise ValueError('Truncated or duplicate QMI TLV')
            tlvs[str(tag)] = wire[pos:pos + length].hex()
            pos += length
        return dict(flags=wire[0], transaction=transaction, message_id=ident,
                    tlvs=tlvs, wire_hex=wire.hex())
    return None


def parse_trace(path):
    pending, packets = {}, []
    complete = unmatched = rejected = 0
    for number, line in enumerate(path.open(encoding='utf-8', errors='strict'), 1):
        match = LINE.match(line.rstrip('\n'))
        if not match:
            continue
        tid, timestamp, body = int(match[1]), float(match[2]), match[3]
        if body.endswith('<unfinished ...>'):
            pending[tid] = (timestamp, body[:-len('<unfinished ...>')], number)
            continue
        resumed = re.match(r'<\.\.\. (\w+) resumed>(.*)', body)
        if resumed:
            previous = pending.pop(tid, None)
            if previous is None:
                unmatched += 1
                continue
            timestamp, prefix, number = previous
            body = prefix + resumed[2]
        complete += 1
        call = re.match(r'(sendto|recvfrom|sendmsg|recvmsg)\((\d+)', body)
        if not call:
            continue
        result = re.search(r'\)\s+=\s+(\d+)(?:\s|$)', body)
        encoded = HEX.search(body)
        if not result or not encoded:
            continue
        raw = bytes.fromhex(encoded[1].replace('\\x', ''))
        # Do not interpret partial sends, truncated receives, or sockaddr bytes.
        if len(raw) != int(result[1]):
            continue
        try:
            decoded = decode_wire(raw)
        except ValueError:
            rejected += 1
            continue
        if decoded is not None:
            packets.append(dict(time=timestamp, tid=tid, fd=int(call[2]),
                                direction='send' if call[1].startswith('send') else 'recv',
                                **decoded, line=number))
    return packets, dict(complete_syscalls=complete, unmatched_resumed=unmatched,
                         pending_at_trace_end=len(pending), rejected_qmi_tlvs=rejected)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize_constellations(indications, quality):
    # QMI enum values, distinct from Android GnssStatus constellation values.
    names = {1: 'GPS', 2: 'Galileo', 3: 'SBAS', 4: 'COMPASS_legacy',
             5: 'GLONASS', 6: 'BeiDou', 7: 'QZSS'}
    totals = collections.defaultdict(collections.Counter)
    maximum = collections.defaultdict(collections.Counter)
    for row in indications:
        if row['message_id'] != 0x25:
            continue
        raw = bytes.fromhex(row['tlvs'].get('16', ''))
        if not raw:
            continue
        quality.sv_list(raw)  # Validate the complete ordinary wire array first.
        per_report = collections.defaultdict(collections.Counter)
        for i in range(raw[0]):
            mask, system, _svid, _health, status, nav, _elev, _az, snr = struct.unpack_from('<IIHBIBfff', raw, 1 + i * 28)
            if not mask & 1:
                continue
            name = names.get(system, 'enum_' + str(system))
            counts = per_report[name]
            counts['entries'] += 1
            if mask & 0x80 and math.isfinite(snr):
                counts['valid_snr'] += 1
                counts['positive'] += int(snr > 0)
                counts['above_25_dbhz'] += int(snr > 25)
                maximum[name]['cn0_dbhz'] = max(maximum[name]['cn0_dbhz'], snr)
            if mask & 8:
                counts['track'] += int(status == 3)
            if mask & 0x10:
                counts['ephemeris'] += int(bool(nav & 1))
                counts['almanac'] += int(bool(nav & 2))
                counts['track_with_ephemeris'] += int(bool(nav & 1) and mask & 8 and status == 3)
        for name, counts in per_report.items():
            totals[name].update(counts)
            for field, count in counts.items():
                key = field + '_per_report'
                maximum[name][key] = max(maximum[name][key], count)
    return dict(ordinary_list_only_no_expanded_duplicates=True,
                totals_by_constellation={k: dict(v) for k, v in totals.items()},
                maximum_by_constellation={k: dict(v) for k, v in maximum.items()})


def summarize(packets, parsing, explicit_fds=None):
    # Identify the live LOC socket from an actual register-events request.
    fds = {p['fd'] for p in packets if p['flags'] == 0 and
           p['direction'] == 'send' and p['message_id'] == 0x21 and
           len(bytes.fromhex(p['tlvs'].get('1', ''))) == 8}
    identification = 'register_events_request'
    if explicit_fds is not None:
        fds = set(explicit_fds)
        if not fds or not fds.issubset({p['fd'] for p in packets}):
            raise ValueError('Explicit LOC socket absent from decoded packets')
        identification = 'explicit_argument_caller_must_verify_process_and_socket_continuity'
    if not fds:
        raise ValueError('No LOC register-events request found; refuse to guess a socket')
    loc = [p for p in packets if p['fd'] in fds]
    indications = [dict(kind='indication', message_id=p['message_id'], tlvs=p['tlvs'])
                   for p in loc if p['direction'] == 'recv' and p['flags'] == 4]
    root = Path(__file__).resolve().parent.parent
    quality = load_module('loc_quality', root / 'kernel246' / 'loc_decode.py')
    measurement = load_module('loc_measurements', root / 'kernel241' / 'measurement_decode.py')
    pqwm = load_module('pqwm_status', root / 'kernel208' / 'pqwm1.py')
    requests = [p for p in loc if p['direction'] == 'send' and p['flags'] == 0]
    ack_counts = collections.Counter()
    for p in requests:
        matches = [a for a in loc if a['direction'] == 'recv' and a['flags'] == 2 and
                   a['fd'] == p['fd'] and a['transaction'] == p['transaction'] and
                   a['message_id'] == p['message_id'] and a['time'] >= p['time']]
        if matches:
            ack = min(matches, key=lambda a: a['time'])
            raw = bytes.fromhex(ack['tlvs'].get('2', ''))
            key = str(struct.unpack('<HH', raw)) if len(raw) == 4 else 'malformed-result'
        else:
            key = 'unmatched'
        ack_counts[key] += 1
    quality_result = quality.summarize(indications)
    # The older Linux observer counted fixes for its fixed session ID only.
    # Android chooses its own session IDs: validate success and coordinates
    # without importing the observer's session-ID restriction.
    successful_positions = 0
    for row in indications:
        if row['message_id'] != 0x24:
            continue
        tlvs = row['tlvs']
        if tlvs.get('1') != '00000000':
            continue
        lat, lon = (bytes.fromhex(tlvs.get(str(tag), '')) for tag in (16, 17))
        if len(lat) != 8 or len(lon) != 8:
            continue
        lat, lon = struct.unpack('<d', lat)[0], struct.unpack('<d', lon)[0]
        successful_positions += int(math.isfinite(lat) and math.isfinite(lon) and
                                    -90 <= lat <= 90 and -180 <= lon <= 180)
    quality_result['nmea'].pop('valid_qmi_position_fixes', None)
    quality_result['successful_qmi_positions_with_valid_coordinates'] = successful_positions
    pqwm_rows, pqwm_errors = [], 0
    for row in indications:
        if row['message_id'] != 0x26:
            continue
        raw = bytes.fromhex(row['tlvs'].get('16') or row['tlvs'].get('1') or '')
        if not raw:
            continue
        try:
            sentences = quality.nmea_text(raw).replace('\r', '').split('\n')
            for sentence in sentences:
                if sentence.startswith('$PQWM1,'):
                    pqwm_rows.append(pqwm.decode(sentence))
        except (ValueError, UnicodeError):
            pqwm_errors += 1
    fields = ['time_valid', 'time_source', 'time_unc_ns', 'clock_bias_unc',
              'xo_state', 'pga_gain', 'adc_i', 'adc_q', 'agc_gps', 'agc_glo',
              'agc_bds', 'agc_gal', 'jammer_gps', 'error_recovery']
    ranges = {}
    for field in fields:
        values = [row[field] for row in pqwm_rows if row[field] is not None]
        ranges[field] = dict(samples=len(values), minimum=min(values) if values else None,
                             maximum=max(values) if values else None)
    return dict(**parsing, qmi_packets=len(packets), loc_socket_fds=sorted(fds),
                loc_socket_identification=identification,
                loc_packets=len(loc), loc_request_counts=dict(collections.Counter(hex(p['message_id']) for p in requests)),
                ack_result_error_counts=dict(ack_counts), quality=quality_result,
                constellations=summarize_constellations(indications, quality),
                measurements=measurement.summarize_measurements(indications),
                pqwm1=dict(reports=len(pqwm_rows), errors=pqwm_errors, ranges=ranges,
                           values_are_reported_fields_not_electrical_measurements=True),
                regression=dict(loc=quality.regression(), measurements=measurement.regression(),
                                pqwm1=pqwm.selftest()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--loc-fd', type=int, action='append',
                        help='Only for an independently verified inherited LOC socket; never guess from message IDs')
    args = parser.parse_args()
    packets, parsing = parse_trace(args.trace)
    report = summarize(packets, parsing, args.loc_fd)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'decoded-qmi-private.json').write_text(json.dumps(packets, indent=2) + '\n')
    (args.output_dir / 'decoded-summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
