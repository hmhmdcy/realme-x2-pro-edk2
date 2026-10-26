"""Synthetic boundary checks of the offline parser and evidence rules."""
from pathlib import Path
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('audit', ROOT / 'audit-ui-cache.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def signal(timestamp, values, path=audit.DISPLAY):
    fields = []
    for name, kind, value in values:
        fields.append('      dict entry(\n         string ' + json.dumps(name) +
                      '\n         variant             ' + kind + ' ' + value + '\n      )\n')
    return (f'signal time={timestamp} sender=:1.5 -> destination=(null destination) serial=10 path={path}; interface=org.freedesktop.DBus.Properties; member=PropertiesChanged\n'
            '   string "org.freedesktop.UPower.Device"\n   array [\n' + ''.join(fields) +
            '   ]\n   array [\n   ]\n')


class ParserTests(unittest.TestCase):
    def test_multiple_types_and_escaped_strings(self):
        text = signal(1000.25, [('State', 'uint32', '2'), ('IconName', 'string', json.dumps('quote"slash\\')),
                               ('Online', 'boolean', 'false'), ('Percentage', 'double', '96.5'),
                               ('UpdateTime', 'uint64', '1792730331')])
        rows, errors = audit.parse_dbus(text)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]['values'], {'State': 2, 'IconName': 'quote"slash\\', 'Online': False,
                                           'Percentage': 96.5, 'UpdateTime': 1792730331})

    def test_multiple_signals_and_wrong_signal(self):
        rows, errors = audit.parse_dbus('signal unrelated\n' + signal(1000, [('State', 'uint32', '1')]) + signal(1001, [('State', 'uint32', '2')]))
        self.assertEqual([row['values']['State'] for row in rows], [1, 2])
        self.assertEqual(errors, [])

    def test_invalid_boolean_not_coerced(self):
        rows, errors = audit.parse_dbus(signal(1000, [('Online', 'boolean', 'garbage')]))
        self.assertEqual(rows[0]['values'], {})
        self.assertEqual(len(errors), 1)

    def test_missing_interface_not_trusted(self):
        rows, errors = audit.parse_dbus(signal(1000, [('State', 'uint32', '1')]).replace('   string "org.freedesktop.UPower.Device"\n', ''))
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 1)

    def test_truncated_body_not_trusted(self):
        text = signal(1000, [('State', 'uint32', '1')]).rsplit(']', 1)[0]
        rows, errors = audit.parse_dbus(text)
        self.assertEqual(rows, [])
        self.assertEqual(len(errors), 1)

    def test_empty_log(self):
        self.assertEqual(audit.parse_dbus(''), ([], []))


class EvidenceTests(unittest.TestCase):
    def test_no_events_cannot_verify_icon(self):
        result = audit.audit({'samples': [], 'duration_seconds': 10})
        self.assertFalse(result['screen_icon_latency_verified'])
        self.assertEqual(result['transitions'], [])
        self.assertEqual(result['clock']['cross_clock_timing_quality'], 'unavailable')

    def test_scalar_invalid_source_not_physical_transition(self):
        rows = [{'t': 0, 'source': {'online': 1}}, {'t': 1, 'source': {'online': {'errno': 61}}},
                {'t': 2, 'source': {'online': 1}}, {'t': 3, 'source': {'online': 0}},
                {'t': 4, 'source': {'online': 1}}]
        self.assertEqual(audit.sample_transitions(rows), [
            {'kind': 'detach', 'online': 0, 'last_old_sample_t': 2, 'first_new_sample_t': 3},
            {'kind': 'attach', 'online': 1, 'last_old_sample_t': 3, 'first_new_sample_t': 4}])

    def test_notifications_do_not_fabricate_physical_transition(self):
        data = {'samples': [{'t': t, 'source': {'online': 1}} for t in range(3)],
                'kernel_events': [{'t': t, 'POWER_SUPPLY_NAME': audit.CHARGER, 'POWER_SUPPLY_ONLINE': '1'} for t in range(3)],
                'duration_seconds': 3}
        result = audit.audit(data)
        self.assertEqual(result['transitions'], [])
        self.assertTrue(any('0.5' in warning for warning in result['warnings']))

    def test_same_clock_kernel_delay_and_estimated_dbus_delay(self):
        data = {'samples': [{'t': 0, 'source': {'online': 1}}, {'t': 1, 'source': {'online': 0}}],
                'kernel_events': [{'t': .3, 'POWER_SUPPLY_NAME': audit.SOURCE, 'POWER_SUPPLY_ONLINE': '0'},
                                  {'t': .4, 'POWER_SUPPLY_NAME': audit.CHARGER, 'POWER_SUPPLY_ONLINE': '0'},
                                  {'t': .9, 'POWER_SUPPLY_NAME': 'bq', 'POWER_SUPPLY_TYPE': 'Battery', 'POWER_SUPPLY_STATUS': 'Discharging'}],
                'start_realtime': 1000, 'upower_dbus_log': signal(1001, [('State', 'uint32', '2')]),
                'duration_seconds': 3}
        result = audit.audit(data)
        self.assertAlmostEqual(result['transitions'][0]['source_to_battery_uevent_seconds'], .6)
        self.assertAlmostEqual(result['transitions'][0]['source_to_display_state_seconds_estimated'], .7)
        self.assertFalse(result['screen_icon_latency_verified'])

    def test_missing_state_signal_not_invented(self):
        result = audit.audit({'samples': [], 'start_realtime': 1000,
                              'upower_dbus_log': signal(1001, [('UpdateTime', 'uint64', '1001')])})
        self.assertEqual(result['upower_display_states'], [])

    def test_clock_jump_is_flagged(self):
        result = audit.audit({'start_realtime': 1000, 'end_realtime': 1020, 'end_monotonic_elapsed': 10})
        self.assertEqual(result['clock']['observed_end_offset_drift_seconds'], 10)
        self.assertTrue(any('unreliable' in warning for warning in result['warnings']))

    def test_wrapper_capture(self):
        result = audit.audit({'capture': {'duration_seconds': 4, 'samples': []}})
        self.assertEqual(result['duration_seconds'], 4)


if __name__ == '__main__':
    unittest.main()
