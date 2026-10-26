"""Audit a single retained physical USB/UI observation; no device access."""
import json
import math
import re
from pathlib import Path
import argparse

SIGNAL = re.compile(r'^signal time=([0-9.]+).*?path=([^; ]+);[^\n]*member=PropertiesChanged[^\n]*\n', re.M)
PROPERTY = re.compile(r'dict entry\(\s*string ("(?:[^"\\]|\\.)*")\s*variant\s+(boolean|u?int(?:16|32|64)|byte|double|string|object path)\s+([^\n]+)', re.M)
DISPLAY = '/org/freedesktop/UPower/devices/DisplayDevice'


def parse_dbus(log):
    heads = list(SIGNAL.finditer(log)); signals, errors = [], []
    for index, head in enumerate(heads):
        body = log[head.end():heads[index + 1].start() if index + 1 < len(heads) else len(log)]
        interface = re.match(r'\s*string ("(?:[^"\\]|\\.)*")', body)
        if not interface or not body.rstrip().endswith(']'):
            errors.append({'index': index, 'reason': 'missing interface or truncated body'}); continue
        try: interface_name = json.loads(interface[1]); realtime = float(head[1])
        except (ValueError, json.JSONDecodeError):
            errors.append({'index': index, 'reason': 'invalid interface or timestamp'}); continue
        values = {}
        for item in PROPERTY.finditer(body):
            try:
                key = json.loads(item[1]); kind, value = item[2], item[3].strip()
                if kind in ['string', 'object path']: value = json.loads(value)
                elif kind == 'boolean':
                    if value not in ['true', 'false']: raise ValueError('bad boolean')
                    value = value == 'true'
                elif kind == 'double':
                    value = float(value)
                    if not math.isfinite(value): raise ValueError('nonfinite double')
                else: value = int(value)
                if key == 'State' and (type(value) is not int or not 0 <= value <= 6):
                    raise ValueError('invalid State enum')
                values[key] = value
            except (ValueError, json.JSONDecodeError):
                errors.append({'index': index, 'reason': 'invalid scalar'})
        if interface_name == 'org.freedesktop.UPower.Device':
            signals.append({'realtime': realtime, 'path': head[2], 'values': values})
    return signals, errors


def mapped_signals(signals, start, end):
    a = (start['m0'] + start['m1']) / 2; b = (end['m0'] + end['m1']) / 2
    drift = (end['real'] - b) - (start['real'] - a)
    bracket = max(start['m1'] - start['m0'], end['m1'] - end['m0'])
    valid = (all(math.isfinite(x) for x in [a, b, start['real'], end['real'], bracket])
             and b > a and end['real'] > start['real'] and abs(drift) <= .05
             and 0 <= bracket <= .05)
    mapped = []
    if valid:
        for signal in signals:
            fraction = (signal['realtime'] - start['real']) / (end['real'] - start['real'])
            mapped.append({**signal, 'estimated_t': fraction * (b - a)})
    return mapped, {'endpoints_consistent': valid, 'endpoint_offset_change_seconds': drift,
                    'anchor_bracket_seconds': bracket,
                    'quality': 'endpoint-based estimates; no proof against cancelling clock steps inside the interval'}


def physical_samples(rows):
    """Rebuild the digital power cycle from raw samples, not worker summary."""
    baseline = off_count = on_count = 0
    ready = off_begin = on_begin = settle = previous = None
    action = off_confirmed = complete = False
    off_span = on_span = 0
    gaps = []
    for index, row in enumerate(rows):
        a, now = row.get('t_start'), row.get('t_end')
        timely = (isinstance(a, (int, float)) and isinstance(now, (int, float))
                  and math.isfinite(a) and math.isfinite(now) and 0 <= a <= now <= a + 2
                  and (previous is None or previous < now and 0 <= a - previous <= 2.5))
        previous = now if isinstance(now, (int, float)) and math.isfinite(now) else None
        if not timely:
            gaps.append(index); baseline = on_count = 0
            if not action: ready = None
            if not off_confirmed: off_count = 0; off_begin = None; off_span = 0
            on_begin = settle = None; on_span = 0; complete = False
            continue
        online = row.get('source_online') == row.get('acok_online') == 1
        offline = row.get('source_online') == row.get('acok_online') == 0
        s = row.get('telemetry', {})
        healthy = (online and all(s.get(k) == 1 for k in ['valid', 'online', 'protection_ok'])
                   and s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) <= 3000
                   and all(s.get(k) == 0 for k in ['error', 'stop_error', 'latched', 'source_inhibit', 'fault']))
        if ready is None:
            baseline = baseline + 1 if healthy else 0
            if baseline >= 3: ready = now
            continue
        if not off_confirmed:
            if not action and not healthy:
                if row.get('source_online') == 0 or row.get('acok_online') == 0: action = True
                else: ready = None; baseline = 0; continue
            if offline:
                action = True
                if not off_count: off_begin = now
                off_count += 1; off_span = now - off_begin
                off_confirmed = off_count >= 3 and off_span >= 2
            else: off_count = 0; off_begin = None; off_span = 0
            continue
        if online:
            if not on_count: on_begin = now
            on_count += 1; on_span = now - on_begin
            if on_count >= 3 and on_span >= 2 and settle is None: settle = now
            complete = settle is not None and now - settle >= 25
        else:
            on_count = 0; on_begin = settle = None; on_span = 0; complete = False
    return {'ready_at': ready, 'offline_confirmed': off_confirmed,
            'offline_begin': off_begin, 'online_begin': on_begin,
            'offline_samples': off_count, 'online_samples': on_count,
            'offline_span': off_span, 'online_span': on_span,
            'settling_complete': complete, 'gap_sample_indices': gaps}


def audit(data):
    signals, parse_errors = parse_dbus(data.get('dbus_log', ''))
    if data.get('clock_start') and data.get('clock_end'):
        mapped, clocks = mapped_signals(signals, data['clock_start'], data['clock_end'])
    else:
        mapped, clocks = [], {'endpoints_consistent': False, 'reason': 'missing start/end clock anchors'}
    rows = data.get('samples', [])
    state = physical_samples(rows)
    monitor = data.get('monitor', {})
    monitor_complete = not monitor.get('errors') and monitor.get('started') is True
    physical = bool(data.get('terminal_reason') == 'cycle_complete' and data.get('identity_unchanged') is True
                    and state['offline_confirmed'] and state['settling_complete']
                    and not data.get('exception') and not data.get('capture_errors')
                    and not data.get('event_read_errors') and monitor_complete)
    events = data.get('kernel_events', [])
    battery_name = data.get('battery_name', '')
    battery_path = '/org/freedesktop/UPower/devices/battery_' + re.sub(r'[^a-zA-Z0-9_]', '_', battery_name)
    edges = []
    for name, value, t, end in [('detach', '0', state.get('offline_begin'), state.get('online_begin')),
                                 ('attach', '1', state.get('online_begin'), data.get('duration_seconds'))]:
        if t is None or end is None: continue
        low, high = max(0, t - 2), end
        selected = [e for e in events if low <= e['t'] <= high]
        def first(predicate): return next((e for e in selected if predicate(e)), None)
        source = first(lambda e: e.get('POWER_SUPPLY_NAME') == 'samurai-usb-input' and e.get('POWER_SUPPLY_ONLINE') == value)
        acok = first(lambda e: e.get('POWER_SUPPLY_NAME') == 'mp2650-input' and e.get('POWER_SUPPLY_ONLINE') == value)
        battery = first(lambda e: e.get('POWER_SUPPLY_NAME') == battery_name and e.get('POWER_SUPPLY_TYPE') == 'Battery')
        item = {'edge': name, 'sample_evidence_t': t, 'source_uevent_t': source['t'] if source else None,
                'acok_uevent_t': acok['t'] if acok else None,
                'battery_uevent_t': battery['t'] if battery else None,
                'battery_kernel_status': battery.get('POWER_SUPPLY_STATUS') if battery else None}
        for label, path in [('battery', battery_path), ('display', DISPLAY)]:
            states = [s for s in mapped if s['path'] == path and low <= s['estimated_t'] <= high and 'State' in s['values']]
            item[label + '_state_events'] = [{'estimated_t': s['estimated_t'], 'state': s['values']['State']} for s in states]
            # Missing State is preserved; UpdateTime/Percentage cannot stand in.
            following = [s for s in states if source and s['estimated_t'] >= source['t']]
            item['source_to_first_following_' + label + '_state_event_seconds_estimated'] = following[0]['estimated_t'] - source['t'] if following else None
        edges.append(item)
    return {'scope': 'one physical power removal/reconnection and notification observation',
            'physical_cycle_passed': physical, 'screen_latency_verified': False,
            'terminal_reason': data.get('terminal_reason'), 'sample_count': len(rows),
            'kernel_event_count': len(events), 'dbus_signal_count': len(signals),
            'monitor_complete': monitor_complete, 'raw_cycle_evidence': state,
            'clock_mapping': clocks, 'dbus_parse_errors': parse_errors, 'edges': edges,
            'sample_status_current_sequence': [{'t_start': r.get('t_start'), 't_end': r.get('t_end'),
                    'source_online': r.get('source_online'), 'acok_online': r.get('acok_online'),
                    'telemetry_flags': r.get('telemetry', {}).get('flags'),
                    'flags_fresh': r.get('flags_fresh'), 'telemetry_age_ms': r.get('telemetry', {}).get('age_ms'),
                    **r.get('battery', {})} for r in rows],
            'notes': ['USB configured state is not used as physical evidence.',
                      'Physical evidence requires continuous source AND ACOK offline then online, with 25s settling.',
                      'No State signal means no measured State latency; net discharge is never rewritten Charging.',
                      'The first following State event is a timing interval, not proof of causality or the intended State.',
                      'All cross-clock event latencies are endpoint-based estimates, not screen presentation times.',
                      'Offline telemetry flags may be cleared by driver collection; flags_fresh marks their scope.']}


def load_directory(directory):
    """Read complete capture or preserve partial logs as unqualified evidence."""
    directory = Path(directory)
    capture = directory / 'capture-private.json'
    if capture.exists(): return json.loads(capture.read_text())
    errors = []; data = {'terminal_reason': 'terminal_unproved_partial_logs', 'identity_unchanged': False}
    for key, filename in [('samples', 'samples-private.jsonl'), ('kernel_events', 'kernel-events-private.jsonl')]:
        data[key] = []
        path = directory / filename
        if path.exists():
            for index, line in enumerate(path.read_text().splitlines()):
                try: data[key].append(json.loads(line))
                except ValueError: errors.append(filename + ': malformed line ' + str(index))
    for key, filename in [('clock_start', 'clock-start.json'), ('clock_end', 'clock-end.json')]:
        path = directory / filename
        if path.exists():
            try: data[key] = json.loads(path.read_text())
            except ValueError: errors.append(filename + ': malformed JSON')
    log = directory / 'upower-dbus-private.log'
    data['dbus_log'] = log.read_text(errors='replace') if log.exists() else ''
    data['capture_errors'] = ['complete terminal capture absent', *errors]
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    args = parser.parse_args(argv)
    print(json.dumps(audit(load_directory(args.directory)), indent=2, allow_nan=False))


if __name__ == '__main__': main()
