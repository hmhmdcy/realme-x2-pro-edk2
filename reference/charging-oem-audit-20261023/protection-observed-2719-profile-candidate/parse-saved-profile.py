"""Explicit-profile schema2 saved diagnostic cache only; no transport or policy API."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import stat
import subprocess

COMMANDS = (1, 0x51, 0x53, 0x54, 0x57, 0x50, 0x52, 0x56)
SIZES = (2, 4, 4, 4, 2, 4, 4, 4)
STATUS_MASK = 0xD860  # Existing classifier OCA/TCA/OTA/TDA/DSG/FC mask.
PROFILES = {'standard': 0, 'observed-2719-0056-3': 1}
HEADER = frozenset('schema diagnostic_profile profile_identity_verified attempted terminal stage error frames_attempted started_ns ended_ns '
                  'battery_before_valid battery_before battery_before_ns battery_after_valid '
                  'battery_after battery_after_ns compatibility_verified'.split())
FRAME = frozenset('frame cmd attempted expected_size select_attempted select_rc read_attempted '
                 'read_rc full_read validate_attempted validate_rc started_ns select_end_ns '
                 'read_end_ns ended_ns raw'.split())
FLAGS = frozenset('profile_identity_verified attempted terminal battery_before_valid battery_after_valid '
                  'select_attempted read_attempted full_read validate_attempted compatibility_verified'.split())
TIMES = frozenset('started_ns ended_ns select_end_ns read_end_ns battery_before_ns battery_after_ns'.split())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fields(line, expected):
    result = {}
    for token in line.split(' '):
        require(re.fullmatch(r'[a-z][a-z0-9_]*=[^\s=]+', token), 'invalid field token')
        key, value = token.split('=')
        require(key not in result, 'duplicate field: ' + key)
        if key == 'raw':
            require(value == 'unavailable' or re.fullmatch(r'[0-9a-f]{72}', value), 'invalid raw frame')
        else:
            require(re.fullmatch(r'-?(?:0|[1-9][0-9]*)|0x[0-9a-f]+', value), 'invalid integer: ' + key)
            value = int(value, 16 if value.startswith('0x') else 10)
            if key in FLAGS:
                require(value in (0, 1), 'invalid flag: ' + key)
            elif key in TIMES:
                require(0 <= value <= (1 << 64) - 1, 'invalid timestamp: ' + key)
            elif key.endswith('_rc') or key == 'error':
                require(-4095 <= value <= 2, 'invalid errno: ' + key)
            else:
                require(0 <= value <= 0xffffffff, 'invalid unsigned value: ' + key)
        result[key] = value
    require(result.keys() == expected, 'missing or unexpected fields')
    return result


def parse_saved_profile(data, decoder, decoder_sha256, *, profile):
    require(profile in PROFILES, 'explicit known diagnostic profile required')
    require(0 < len(data) < 4096 and data.endswith(b'\n'), 'truncated or oversized sysfs report')
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('non-ASCII report') from exc
    lines = text.splitlines()
    require(len(lines) == 9 and '\r' not in text, 'expected one header and eight frames')
    header = fields(lines[0], HEADER)
    frames = [fields(line, FRAME) for line in lines[1:]]
    require(header['schema'] == 2 and header['diagnostic_profile'] == PROFILES[profile] and
            header['compatibility_verified'] == 0, 'schema2/profile mismatch; never relabel legacy cache')
    sizes = SIZES[:-1] + ((3 if PROFILES[profile] == 1 and header['profile_identity_verified'] else 4),)
    n = header['frames_attempted']
    require(0 <= n <= 8 and 0 <= header['stage'] <= 6, 'invalid batch counters')
    require(header['battery_before'] <= 0xffff and header['battery_after'] <= 0xffff, 'invalid BatteryStatus')
    require(header['error'] <= 0, 'positive batch error')
    require(bool(header['terminal']) == bool(header['attempted']), 'nonterminal capture cannot be a sysfs snapshot')
    require(bool(n) == bool(header['attempted']), 'attempt counter contradicts claim')
    if header['attempted']:
        require(header['started_ns'] <= header['ended_ns'], 'reversed batch interval')
        require((header['stage'] == 6) == (header['error'] == 0), 'stage/error contradiction')
    else:
        require(all(value == 0 for key, value in header.items() if key not in ('schema', 'diagnostic_profile')), 'nonzero unattempted header')
    arguments = [str(decoder), '--profile', profile]
    complete_indices = []
    previous_end = header['started_ns']
    for i, frame in enumerate(frames):
        require(frame['frame'] == i and frame['cmd'] == COMMANDS[i], 'frame order/command mismatch')
        require(frame['expected_size'] == (sizes[i] if header['attempted'] else 0), 'payload size mismatch')
        require(bool(frame['attempted']) == (i < n), 'noncontiguous attempted frames')
        if not frame['attempted']:
            zero_keys = FRAME - {'frame', 'cmd', 'expected_size', 'raw'}
            require(all(frame[k] == 0 for k in zero_keys) and frame['raw'] == 'unavailable', 'nonzero unattempted frame')
            continue
        require(frame['select_attempted'] == 1 and frame['select_rc'] <= 0, 'invalid selector receipt')
        require(frame['started_ns'] >= previous_end and frame['ended_ns'] <= header['ended_ns'], 'frame outside ordered batch')
        require(frame['started_ns'] <= frame['select_end_ns'] <= frame['ended_ns'], 'reversed selector interval')
        require(bool(frame['read_attempted']) == (frame['select_rc'] == 0), 'selector/read contradiction')
        if frame['read_attempted']:
            require(frame['select_end_ns'] <= frame['read_end_ns'] <= frame['ended_ns'], 'reversed read interval')
        else:
            require(frame['read_end_ns'] == frame['read_rc'] == 0, 'unattempted read has result')
        full = frame['read_attempted'] and frame['read_rc'] == 2
        require(bool(frame['full_read']) == bool(full) == bool(frame['validate_attempted']), 'completion/validation contradiction')
        require(frame['validate_rc'] <= 0, 'positive validation error')
        if full:
            require(frame['raw'] != 'unavailable', 'complete read missing raw bytes')
            arguments.extend((f'{COMMANDS[i]:04x}', frame['raw']))
            complete_indices.append(i)
        else:
            require(frame['raw'] == 'unavailable' and frame['validate_rc'] == 0, 'partial read claims validated bytes')
        previous_end = frame['ended_ns']
    decoder = Path(decoder)
    require(re.fullmatch('[0-9a-f]{64}', decoder_sha256), 'invalid decoder SHA')
    require(decoder.is_file() and hashlib.sha256(decoder.read_bytes()).hexdigest() == decoder_sha256, 'decoder identity mismatch')
    decoded = []
    if complete_indices:
        run = subprocess.run(arguments, capture_output=True, check=False)
        require(run.returncode == 0 and not run.stderr, 'saved-frame decoder failed')
        decoded = json.loads(run.stdout)
        require(len(decoded) == len(complete_indices), 'decoder result count mismatch')
        for index, item in zip(complete_indices, decoded):
            frame = frames[index]
            require(item['command'] == frame['cmd'] and item['payload_bytes'] == frame['expected_size'], 'decoder command mismatch')
            require(item['validate_rc'] == frame['validate_rc'], 'raw bytes contradict provider validation')
            frame['decoded'] = item
    identity = frames[0].get('decoded', {})
    identity_verified = (identity.get('validate_rc') == 0 and identity.get('value') == 0x2719)
    require(bool(header['profile_identity_verified']) == identity_verified, 'profile lacks this batch identity proof')
    for key in ('before', 'after'):
        if header[f'battery_{key}_valid']:
            require(header['started_ns'] <= header[f'battery_{key}_ns'] <= header['ended_ns'], 'BatteryStatus outside batch')
    if header['battery_before_valid']:
        require(frames[0]['ended_ns'] <= header['battery_before_ns'], 'BatteryStatus precedes identity')
        if n > 1:
            require(header['battery_before_ns'] <= frames[1]['started_ns'], 'BatteryStatus follows first status frame')
    if header['battery_after_valid']:
        require(header['battery_before_valid'] and n == 8 and frames[-1]['ended_ns'] <= header['battery_after_ns'], 'invalid trailing BatteryStatus')
    sequence_complete = (header['attempted'] == header['terminal'] == 1 and header['stage'] == 6
                         and header['error'] == 0 and n == 8 and len(decoded) == 8
                         and all(d['validate_rc'] == 0 for d in decoded)
                         and decoded[0]['value'] == 0x2719
                         and header['battery_before_valid'] == header['battery_after_valid'] == 1)
    require(header['stage'] != 6 or sequence_complete, 'complete stage contradicts raw sequence')
    stable = None
    if header['battery_before_valid'] and header['battery_after_valid']:
        stable = not ((header['battery_before'] ^ header['battery_after']) & STATUS_MASK)
    return {'schema': 'samurai-explicit-profile-mac-analysis-v2', 'diagnostic_profile': profile,
            'input_sha256': hashlib.sha256(data).hexdigest(), 'decoder_sha256': decoder_sha256,
            'header': header, 'frames': frames, 'sequence_complete': bool(sequence_complete),
            'battery_status_mask': STATUS_MASK, 'battery_status_mask_stable': stable,
            'batch_duration_ns': header['ended_ns'] - header['started_ns'] if header['attempted'] else None,
            'compatibility_verified': False, 'freshness_verified': False, 'boot_identity_verified': False,
            'TCA_classification': 'UNVERIFIED', 'charge_or_recharge_authorized': False,
            'physical_safety_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--decoder', type=Path, required=True)
    parser.add_argument('--decoder-sha256', required=True)
    parser.add_argument('--profile', choices=tuple(PROFILES), required=True)
    args = parser.parse_args()
    source = args.input.resolve()
    require(not any(source.is_relative_to(Path(root)) for root in ('/sys', '/proc', '/dev')), 'use a saved ordinary file')
    require(stat.S_ISREG(source.stat().st_mode) and source.stat().st_size < 4096, 'invalid saved file')
    print(json.dumps(parse_saved_profile(source.read_bytes(), args.decoder.resolve(), args.decoder_sha256, profile=args.profile), indent=2))


if __name__ == '__main__':
    main()
