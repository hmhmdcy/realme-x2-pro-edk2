"""Audit cached usb-hotplug capture only. No device access or live observers.

Reports notification timing, not compositor/panel latency. Kernel event times
are receiver MONOTONIC times; dbus-monitor timestamps are REALTIME. The legacy
capture has one clock anchor, so cross-clock timings are explicitly estimates.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import json
import math
import re
import statistics

DISPLAY = '/org/freedesktop/UPower/devices/DisplayDevice'
SOURCE = 'samurai-usb-input'
CHARGER = 'mp2650-input'
STATES = {0: 'Unknown', 1: 'Charging', 2: 'Discharging', 3: 'Empty',
          4: 'FullyCharged', 5: 'PendingCharge', 6: 'PendingDischarge'}
SIGNAL = re.compile(r'^signal time=([0-9.]+).*?path=([^; ]+);[^\n]*member=PropertiesChanged[^\n]*\n', re.M)
PROPERTY = re.compile(r'dict entry\(\s*string ("(?:[^"\\]|\\.)*")\s*variant\s+(boolean|u?int(?:16|32|64)|byte|double|string|object path)\s+([^\n]+)', re.M)


def scalar(kind, text):
    text = text.strip()
    if kind in ['string', 'object path']:
        return json.loads(text)
    if kind == 'boolean':
        if text not in ['true', 'false']:
            raise ValueError('invalid D-Bus boolean')
        return text == 'true'
    value = float(text) if kind == 'double' else int(text)
    if not math.isfinite(value):
        raise ValueError('non-finite D-Bus value')
    return value


def parse_dbus(log):
    """Parse scalar PropertiesChanged dictionaries; retain no sender identity."""
    heads = list(SIGNAL.finditer(log))
    signals, errors = [], []
    for index, head in enumerate(heads):
        body = log[head.end():heads[index + 1].start() if index + 1 < len(heads) else len(log)]
        interface = re.match(r'\s*string ("(?:[^"\\]|\\.)*")', body)
        if not interface:
            errors.append({'signal_index': index, 'reason': 'missing interface'})
            continue
        if not body.rstrip().endswith(']'):
            errors.append({'signal_index': index, 'reason': 'truncated PropertiesChanged body'})
            continue
        values = {}
        for item in PROPERTY.finditer(body):
            name = json.loads(item[1])
            try:
                values[name] = scalar(item[2], item[3])
            except (ValueError, json.JSONDecodeError) as error:
                errors.append({'signal_index': index, 'property': name, 'reason': str(error)})
        signals.append({'realtime': float(head[1]), 'path': head[2],
                        'interface': json.loads(interface[1]), 'values': values})
    return signals, errors


def sample_transitions(rows):
    """Intervals bracket observed source attachment; no exact physical times."""
    result, previous = [], None
    for row in rows:
        online = row.get('source', {}).get('online')
        if type(online) is not int or online not in [0, 1]:
            continue
        if previous is not None and online != previous['source']['online']:
            result.append({'kind': 'attach' if online else 'detach', 'online': online,
                           'last_old_sample_t': previous['t'], 'first_new_sample_t': row['t']})
        previous = row
    return result


def online(event):
    value = event.get('POWER_SUPPLY_ONLINE')
    return int(value) if value in ['0', '1'] else None


def event_summary(events, duration):
    counts = Counter(event.get('POWER_SUPPLY_NAME', '?') for event in events)
    result = {}
    for name, count in sorted(counts.items()):
        selected = [event for event in events if event.get('POWER_SUPPLY_NAME', '?') == name]
        gaps = [b['t'] - a['t'] for a, b in zip(selected, selected[1:])]
        result[name] = {'events': count, 'rate_per_second': count / duration if duration > 0 else None,
                        'median_gap_seconds': statistics.median(gaps) if gaps else None,
                        'minimum_gap_seconds': min(gaps) if gaps else None,
                        'online_values': sorted({online(e) for e in selected if online(e) is not None}),
                        'status_values': sorted({e['POWER_SUPPLY_STATUS'] for e in selected if 'POWER_SUPPLY_STATUS' in e})}
    return result


def next_between(items, low, high, predicate):
    return next((item for item in items if low <= item['t'] < high and predicate(item)), None)


def audit(data):
    if 'capture' in data:
        data = data['capture']
    rows = data.get('samples', [])
    events = sorted(data.get('kernel_events', []), key=lambda event: event['t'])
    signals, parse_errors = parse_dbus(data.get('upower_dbus_log', ''))
    duration = data.get('duration_seconds', max([e['t'] for e in events] + [r['t'] for r in rows] + [0]))
    anchor = data.get('start_realtime')
    # A second anchor is supported for newer caches but cannot be invented for
    # legacy captures. Observed offset drift only tests anchor consistency.
    end_real, end_mono = data.get('end_realtime'), data.get('end_monotonic_elapsed')
    drift = (end_real - anchor - end_mono) if all(isinstance(v, (int, float)) for v in [anchor, end_real, end_mono]) else None
    mapped = []
    if isinstance(anchor, (int, float)):
        mapped = [{**signal, 't': signal['realtime'] - anchor} for signal in signals]
    transitions = sample_transitions(rows)
    timeline = []
    for index, transition in enumerate(transitions):
        low = transition['last_old_sample_t']
        high = transitions[index + 1]['last_old_sample_t'] if index + 1 < len(transitions) else duration + .001
        source_event = next_between(events, low, high, lambda e: e.get('POWER_SUPPLY_NAME') == SOURCE and online(e) == transition['online'])
        # A native supply notification is the anchor. If absent, preserve the
        # sample bracket and report incomplete evidence rather than substitute.
        notification_t = source_event['t'] if source_event else None
        earliest = notification_t if notification_t is not None else low
        charger_event = next_between(events, earliest, high, lambda e: e.get('POWER_SUPPLY_NAME') == CHARGER and online(e) == transition['online'])
        batteries = [e for e in events if e.get('POWER_SUPPLY_TYPE') == 'Battery' and earliest <= e['t'] < high]
        battery = batteries[0] if batteries else None
        display = [s for s in mapped if s['path'] == DISPLAY and earliest <= s['t'] < high and any(k in s['values'] for k in ['State', 'IconName', 'Percentage'])]
        state_changes = [s for s in display if 'State' in s['values']]
        first_state = state_changes[0] if state_changes else None
        entry = {**transition, 'source_uevent_t': notification_t,
                 'charger_uevent_t': charger_event['t'] if charger_event else None,
                 'first_battery_uevent_t': battery['t'] if battery else None,
                 'first_battery_status': battery.get('POWER_SUPPLY_STATUS') if battery else None,
                 'battery_statuses_seen': sorted({e['POWER_SUPPLY_STATUS'] for e in batteries if 'POWER_SUPPLY_STATUS' in e}),
                 'first_display_property_signal_estimated_t': display[0]['t'] if display else None,
                 'first_display_state_signal_estimated_t': first_state['t'] if first_state else None,
                 'first_display_state': STATES.get(first_state['values']['State'], str(first_state['values']['State'])) if first_state else None,
                 'display_state_sequence': [{'estimated_t': s['t'], 'state': STATES.get(s['values']['State'], str(s['values']['State']))} for s in state_changes]}
        if notification_t is not None:
            entry['source_to_battery_uevent_seconds'] = battery['t'] - notification_t if battery else None
            entry['source_to_display_state_seconds_estimated'] = first_state['t'] - notification_t if first_state else None
        timeline.append(entry)
    summary = event_summary(events, duration)
    warnings = []
    if not events:
        warnings.append('No kernel event cache: notification latency unmeasurable.')
    if not signals:
        warnings.append('No parsable UPower PropertiesChanged signals: desktop pipeline unverified.')
    if anchor is None:
        warnings.append('Missing REALTIME anchor: no D-Bus/kernel timing correlation.')
    elif drift is None:
        warnings.append('One REALTIME/MONOTONIC anchor only: cross-clock timings assume no wall-clock step/drift; they are estimates.')
    elif abs(drift) > .05:
        warnings.append('Clock anchor offsets differ by more than 50ms: cross-clock latency is unreliable.')
    if summary.get(CHARGER, {}).get('rate_per_second', 0) >= .5:
        warnings.append('Charger emits at least 0.5 change events/s; supplied_to may refresh the original gauge every poll even at steady state.')
    for transition in timeline:
        if transition['kind'] == 'detach' and transition['first_battery_status'] == 'Full':
            warnings.append('Battery still reports Full after unplug: bq27xxx prioritizes FC over signed current; this alone is not lost notification evidence.')
    warnings.append('No compositor/panel timestamp: neither a D-Bus signal nor derived icon proves physical screen update latency.')
    property_counts = Counter((s['path'].rsplit('/', 1)[-1], key) for s in signals for key in s['values'])
    battery_display = [s for s in mapped if s['path'] == DISPLAY]
    battery_display_times = [s['t'] for s in battery_display if 'UpdateTime' in s['values']]
    battery_display_gaps = [b - a for a, b in zip(battery_display_times, battery_display_times[1:])]
    # Standalone battery notifications can establish userspace response time
    # even when no physical plug transition occurred in the observation.
    battery_responses = []
    for event in events:
        if event.get('POWER_SUPPLY_TYPE') != 'Battery':
            continue
        target = next_between(battery_display, event['t'], event['t'] + 5,
                              lambda s: 'State' in s['values'] or 'UpdateTime' in s['values'])
        battery_responses.append({'battery_uevent_t': event['t'],
                                  'kernel_status': event.get('POWER_SUPPLY_STATUS'),
                                  'kernel_current_ua': int(event['POWER_SUPPLY_CURRENT_NOW']) if 'POWER_SUPPLY_CURRENT_NOW' in event else None,
                                  'display_signal_estimated_t': target['t'] if target else None,
                                  'response_seconds_estimated': target['t'] - event['t'] if target else None,
                                  'display_state': STATES.get(target['values'].get('State')) if target else None,
                                  'association': 'first following relevant DisplayDevice signal within 5s; temporal association only'})
    return {'scope': 'cached notification pipeline audit; no phone operations',
            'duration_seconds': duration, 'samples': len(rows), 'kernel_events': len(events),
            'dbus_signals': len(signals), 'dbus_parse_errors': parse_errors,
            'clock': {'start_realtime_present': anchor is not None, 'observed_end_offset_drift_seconds': drift,
                      'cross_clock_timing_quality': 'estimated_single_anchor' if anchor is not None and drift is None else 'anchor_consistency_checked' if drift is not None else 'unavailable'},
            'notification_counts': summary, 'transitions': timeline,
            'dbus_property_counts': [{'device': device, 'property': key, 'signals': count}
                                     for (device, key), count in sorted(property_counts.items())],
            'display_update_median_gap_seconds': statistics.median(battery_display_gaps) if battery_display_gaps else None,
            'battery_notification_responses': battery_responses,
            'upower_display_states': [{'estimated_t': s.get('t'), 'state': STATES.get(s['values']['State'], str(s['values']['State']))} for s in mapped if s['path'] == DISPLAY and 'State' in s['values']],
            'warnings': warnings,
            'screen_icon_latency_verified': False,
            'legacy_capture_limitations': ['Samples timestamped before multiple sequential reads, without an end timestamp.',
                                           'Netlink timestamp is userspace reception, not physical VBUS edge.',
                                           'PropertiesChanged may omit State when it remains unchanged; absence is not a failed refresh.',
                                           'Initial UPower/display properties are not in this capture.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = args.capture.read_bytes()
    result = audit(json.loads(payload))
    result['capture_sha256'] = hashlib.sha256(payload).hexdigest()
    result['auditor_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'transitions': len(result['transitions']), 'kernel_events': result['kernel_events'],
                      'dbus_signals': result['dbus_signals'], 'screen_icon_latency_verified': False}))
