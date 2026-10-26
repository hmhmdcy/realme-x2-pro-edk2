"""Arithmetic on an existing capture only; no collector or test import."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
CAPTURE = Path('E:/edk2-samurai-out/charging-ui-audit-20261023/icon-capture-r8-eud-off/charging-icon-r8-eud-off-001/fetch-1792777440760431917/capture/capture-private.json')


def main():
    raw_bytes = CAPTURE.read_bytes(); data = json.loads(raw_bytes)
    start, end = data['clock_start'], data['clock_end']
    duration = (end['m0']+end['m1']-start['m0']-start['m1'])/2
    def mapped(real):
        return (real-start['real'])*duration/(end['real']-start['real'])
    text = data['dbus_log']
    headers = list(re.finditer(r'^signal time=([0-9.]+).*?path=([^; ]+);[^\n]*member=PropertiesChanged[^\n]*\n', text, re.M))
    dbus = []
    for index, header in enumerate(headers):
        body = text[header.end():headers[index+1].start() if index+1<len(headers) else len(text)]
        event = {'t': mapped(float(header[1])), 'object': header[2].split('/')[-1]}
        state = re.search(r'string "State"\s+variant\s+uint32 (\d+)', body)
        online = re.search(r'string "Online"\s+variant\s+boolean (true|false)', body)
        battery = re.search(r'string "OnBattery"\s+variant\s+boolean (true|false)', body)
        if state: event['State'] = int(state[1])
        if online: event['Online'] = online[1]=='true'
        if battery: event['OnBattery'] = battery[1]=='true'
        event['keys'] = re.findall(r'dict entry\(\s*string "([^"]+)"', body)
        if 188 <= event['t'] <= 210:
            dbus.append(event)
    rows = []
    for row in data['samples']:
        if not 188 <= row['t_end'] <= 210: continue
        t = row['telemetry']
        rows.append({key: row.get(key) for key in ['t_start', 't_end', 'source_online', 'acok_online']}
                    | {'instant_ua': t.get('gauge_current_ua'), 'telemetry_valid': t.get('valid'),
                       'telemetry_age_ms': t.get('age_ms'), 'flags': t.get('flags'),
                       'error': t.get('error'), 'desired_enable': t.get('desired_enable'),
                       'budget_ua': t.get('budget_ua'), 'battery': row['battery'],
                       'source': row['source'], 'hardware_input': row['hardware_input']})
    events = []
    keys = ['t', 'POWER_SUPPLY_NAME', 'POWER_SUPPLY_STATUS', 'POWER_SUPPLY_ONLINE',
            'POWER_SUPPLY_CURRENT_NOW', 'POWER_SUPPLY_CURRENT_MAX', 'POWER_SUPPLY_INPUT_CURRENT_LIMIT']
    for event in data['kernel_events']:
        if 188 <= event['t'] <= 210:
            events.append({key: event[key] for key in keys if key in event})
    result = {'source_capture_sha256': hashlib.sha256(raw_bytes).hexdigest(),
              'scope': 'one retained physical capture; event mapping and sequential sampled fields, no pixel or isolated cause proof',
              'clock_start_bracket_seconds': start['m1']-start['m0'],
              'clock_end_bracket_seconds': end['m1']-end['m0'],
              'duration_monotonic_seconds': duration, 'duration_realtime_seconds': end['real']-start['real'],
              'rows': rows, 'kernel_events': events, 'dbus_events': dbus}
    (HERE/'timeline.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
