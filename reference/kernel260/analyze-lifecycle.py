#!/usr/bin/env python3
"""Publish only verified power/lifecycle aggregates from private USB exports."""
from pathlib import Path
import argparse, hashlib, importlib.util, json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_directory', type=Path)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    private, output = args.private_directory, args.output_directory
    manifest = json.loads((private/'usb-retrieval-manifest-private.json').read_text())
    for entry in manifest:
        data = (private/'usb-retrieved'/entry['name']).read_bytes()
        assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']
    directory = private/'usb-retrieved'
    state = json.loads((directory/'policy-usb/progress.json').read_text())
    assert state['phase'] == 'complete' and len(state['rounds']) == 4
    assert all(v['started'] and v['stopped'] and v['client_deleted'] and v['returncode'] == 0
               for v in state['rounds'])
    assert state['location_settings_restored_without_manual_normalization'] and state['power_unchanged']
    assert state['last']['power'] == 2 and state['power_policy']['online_requests'] == 2
    assert state['power_policy']['low_requests'] == 2 and not state['power_policy']['owned']
    samples = [json.loads(v) for v in (directory/'policy-usb/samples-private.jsonl').read_text().splitlines()]
    transitions = [dict(elapsed_seconds=v['elapsed'], mm_power=v['power'],
                        dms_mode=v['dms_mode']) for v in samples if 'dms_mode' in v]
    assert {v['dms_mode'] for v in transitions} == {'online', 'low-power'}
    assert transitions[-1]['dms_mode'] == 'low-power'
    test_log = (directory/'deployment/phone-policy-tests-private.log').read_text()
    assert 'Ran 14 tests' in test_log and '\nOK\n' in test_log
    installation = json.loads((directory/'deployment/installation-validation.json').read_text())
    assert installation['phase'] == 'complete' and installation['modem_owner_unchanged']
    report = dict(stage=260, exports_sha_verified=len(manifest),
                  compressed_export_bytes=(private/'usb-retrieval-private.zip').stat().st_size,
                  application_cycles=state['rounds'],
                  policy=state['power_policy'], dms_independent_readbacks=transitions,
                  final_gps_settings=state['final_without_normalization'],
                  original_desktop_setting_restored=state['desktop_setting_restored'],
                  original_geoclue_configuration_unchanged=state['base_config_unchanged'],
                  settings_restored_without_manual_normalization=True,
                  final_power=2, taint=state['taint'],
                  hardware_position='returned indoors; exact placement not reconfirmed',
                  time_preparation_completed_after_these_cycles=True,
                  fresh_outdoor_desktop_coordinates_not_yet_verified_at_usb_cycle_capture=True,
                  production_policy_regression_cases_passed_on_phone=14)
    output.mkdir(parents=True, exist_ok=True)
    (output/'lifecycle-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    (output/'installation-validation.json').write_text(json.dumps(installation, indent=2)+'\n')
    for label, source in [('initial-online', 'power-online/state.json'),
                          ('low-power-cycle', 'power-low-cycle/state.json')]:
        value = json.loads((directory/source).read_text())
        (output/(label+'-validation.json')).write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps(dict(exports_verified=len(manifest), application_cycles=4,
                         automatic_online_cycles=2, automatic_low_cycles=2,
                         independent_mode_readbacks=len(transitions),
                         final_power=2, preferences_restored=True)))


if __name__ == '__main__':
    main()
