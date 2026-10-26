"""Decode public LOC layouts without exporting coordinates or satellite identities."""
import collections
import math
import struct


def uint(tlvs, tag, width):
    raw = bytes.fromhex(tlvs.get(str(tag), ''))
    if not raw:
        return None
    if len(raw) != width:
        raise ValueError('Unexpected fixed LOC field length')
    return int.from_bytes(raw, 'little')


def sv_list(raw, expanded=False):
    stride, maximum = (29, 176) if expanded else (28, 80)
    if not raw or raw[0] > maximum or len(raw) != 1 + raw[0] * stride:
        raise ValueError('Invalid LOC SV array length')
    summary = dict(entries=raw[0], valid_snr=0, positive_snr=0, zero_snr=0,
                   invalid_or_nonfinite_snr=0, valid_search=0, valid_track=0,
                   minimum_snr=None, maximum_snr=None)
    for i in range(raw[0]):
        mask, _system, _svid, _health, status, _nav, _elev, _az, snr = struct.unpack_from('<IIHBIBfff', raw, 1 + i * stride)
        if mask & 0x80 and math.isfinite(snr):
            summary['valid_snr'] += 1
            summary['positive_snr'] += int(snr > 0)
            summary['zero_snr'] += int(snr == 0)
            summary['minimum_snr'] = snr if summary['minimum_snr'] is None else min(summary['minimum_snr'], snr)
            summary['maximum_snr'] = snr if summary['maximum_snr'] is None else max(summary['maximum_snr'], snr)
        else:
            summary['invalid_or_nonfinite_snr'] += 1
        if mask & 0x08:
            summary['valid_search'] += int(status == 2)
            summary['valid_track'] += int(status == 3)
    return summary


def nmea_text(raw):
    if raw.startswith(b'$'):
        return raw.rstrip(b'\0').decode('ascii')
    for width in [1, 2, 4]:
        if len(raw) > width and int.from_bytes(raw[:width], 'little') == len(raw) - width and raw[width:width+1] == b'$':
            return raw[width:].rstrip(b'\0').decode('ascii')
    raise ValueError('Unknown LOC NMEA string framing')


def summarize(records):
    counts = collections.Counter()
    commands = []
    sv = collections.Counter()
    snr_min = snr_max = None
    nmea_types = collections.Counter()
    nmea_counts = collections.Counter()
    engine, sessions, positions = [], [], collections.Counter()
    errors = []
    sv_tags = collections.Counter()
    for row in records:
        if row['kind'] == 'command':
            item = {k: row[k] for k in ['message_id', 'matching_ack', 'ack_result', 'ack_error', 'indication_received', 'indication_status']}
            if row['message_id'] == 0x33:
                item.update(horizontal_accuracy=uint(row['ind_tlvs'], 16, 4),
                            intermediate=uint(row['ind_tlvs'], 17, 4),
                            minimum_interval_ms=uint(row['ind_tlvs'], 18, 4))
            if row['message_id'] in [0x21, 0x22, 0x23]:
                item['request_tlvs'] = row['request_tlvs']
            commands.append(item)
        if row['kind'] != 'indication':
            continue
        ident, tlvs = row['message_id'], row['tlvs']
        counts[str(ident)] += 1
        try:
            if ident == 0x25:
                sv_tags.update(tlvs.keys())
                found = False
                for tag, expanded in [(16, False), (17, True)]:
                    if str(tag) not in tlvs:
                        continue
                    found = True
                    parsed = sv_list(bytes.fromhex(tlvs[str(tag)]), expanded)
                    sv['expanded_reports' if expanded else 'ordinary_reports'] += 1
                    for name in ['entries', 'valid_snr', 'positive_snr', 'zero_snr', 'invalid_or_nonfinite_snr', 'valid_search', 'valid_track']:
                        sv[name] += parsed[name]
                    if parsed['minimum_snr'] is not None:
                        snr_min = parsed['minimum_snr'] if snr_min is None else min(snr_min, parsed['minimum_snr'])
                        snr_max = parsed['maximum_snr'] if snr_max is None else max(snr_max, parsed['maximum_snr'])
                if not found:
                    sv['reports_without_either_list'] += 1
            elif ident == 0x2b:
                engine.append(uint(tlvs, 1, 4))
            elif ident == 0x2c:
                sessions.append(dict(state=uint(tlvs, 1, 4), session_id=uint(tlvs, 16, 1)))
            elif ident == 0x24:
                status = uint(tlvs, 1, 4)
                positions[str(status)] += 1
                if status == 0 and uint(tlvs, 2, 1) == 226:
                    a, b = bytes.fromhex(tlvs.get('16', '')), bytes.fromhex(tlvs.get('17', ''))
                    if len(a) == len(b) == 8:
                        lat, lon = struct.unpack('<d', a)[0], struct.unpack('<d', b)[0]
                        nmea_counts['valid_qmi_position_fixes'] += int(math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180)
            elif ident == 0x26:
                nmea_counts['messages'] += 1
                expanded = bytes.fromhex(tlvs.get('16', ''))
                ordinary = bytes.fromhex(tlvs.get('1', ''))
                if expanded:
                    nmea_counts['expanded_string_reports'] += 1
                    text = nmea_text(expanded)
                elif ordinary:
                    nmea_counts['ordinary_string_reports'] += 1
                    text = nmea_text(ordinary)
                else:
                    nmea_counts['reports_without_either_string'] += 1
                    continue
                for sentence in text.replace('\r', '').split('\n'):
                    if not sentence:
                        continue
                    body, checksum = sentence.rsplit('*', 1)
                    value = 0
                    for char in body[1:]:
                        value ^= ord(char)
                    if not body.startswith('$') or len(checksum) != 2 or value != int(checksum, 16):
                        nmea_counts['checksum_errors'] += 1
                        continue
                    fields = body[1:].split(',')
                    name = fields[0]
                    nmea_types[name] += 1
                    if name.endswith('GGA') and len(fields) > 6:
                        nmea_counts['valid_gga'] += int(fields[6].isdigit() and int(fields[6]) > 0)
                    if name.endswith('RMC') and len(fields) > 2:
                        nmea_counts['active_rmc'] += int(fields[2] == 'A')
                    if name.endswith('GSV'):
                        for i in range(7, len(fields), 4):
                            if not fields[i]:
                                continue
                            value = float(fields[i])
                            if math.isfinite(value):
                                nmea_counts['valid_gsv_cnr_fields'] += 1
                                nmea_counts['positive_gsv_cnr_fields'] += int(value > 0)
        except (ValueError, KeyError, struct.error, UnicodeError):
            errors.append(dict(message_id=ident, error='layout_or_value_invalid'))
    return dict(indication_counts=dict(counts), commands=commands, sv=dict(sv), sv_tlv_counts=dict(sv_tags),
                snr_minimum=snr_min, snr_maximum=snr_max, engine_states=engine, session_states=sessions,
                position_status_counts=dict(positions), nmea=dict(nmea_counts), nmea_types=dict(nmea_types),
                decode_errors=errors, missing_snr_not_counted_as_zero=True,
                expanded_list_supported=True, expanded_nmea_string_supported=True,
                sv_entries_include_both_formats_when_firmware_reports_both=True,
                criteria_scope_or_activity_not_inferred=True)


def regression():
    # Concrete old-observer blind spot: expanded-only report with a valid TRACK/SNR.
    entry = struct.pack('<IIHBIBfff', 0x8b, 1, 7, 0, 3, 0, 12., 34., 27.)
    a = sv_list(b'\x01' + entry + b'\x00', True)
    assert a['positive_snr'] == a['valid_track'] == 1
    message = summarize([dict(kind='indication', message_id=0x25, tlvs={'17': (b'\x01' + entry + b'\x00').hex()})])
    assert message['sv']['expanded_reports'] == message['sv']['positive_snr'] == 1
    assert message['sv_tlv_counts'] == {'17': 1} and not message['decode_errors']
    nmea = b'GPGSV,1,1,01,07,12,034,27'
    checksum = 0
    for char in nmea:
        checksum ^= char
    sentence = b'$' + nmea + b'*' + ('%02X' % checksum).encode()
    message = summarize([dict(kind='indication', message_id=0x26, tlvs={'1': '', '16': sentence.hex()})])
    assert message['nmea']['expanded_string_reports'] == message['nmea']['positive_gsv_cnr_fields'] == 1
    assert message['nmea_types'] == {'GPGSV': 1} and not message['decode_errors']
    invalid = struct.pack('<IIHBIBfff', 0, 1, 7, 0, 3, 0, 12., 34., 0.)
    b = sv_list(b'\x01' + invalid)
    assert b['zero_snr'] == b['valid_snr'] == b['valid_track'] == 0
    assert b['invalid_or_nonfinite_snr'] == 1
    nan = struct.pack('<IIHBIBfff', 0x80, 1, 7, 0, 0, 0, 0., 0., float('nan'))
    assert sv_list(b'\x01' + nan)['valid_snr'] == 0
    for malformed in [b'', b'\x01', b'\x00\x00', b'\x01' + entry + b'\x00']:
        try:
            sv_list(malformed)
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed ordinary list accepted')
    return dict(expanded_only_valid_track_and_snr_verified=True, expanded_only_nmea_and_gsv_parsed=True,
                absent_validity_not_reported_as_zero=True,
                nonfinite_snr_excluded=True, malformed_array_lengths_rejected=True)
