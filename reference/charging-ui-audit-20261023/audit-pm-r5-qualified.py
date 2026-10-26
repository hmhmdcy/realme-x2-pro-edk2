"""Read retained r5 evidence and write a separate qualified result only."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import types

ROOT = Path(__file__).resolve().parent


def ordered_log_tail(before, after):
    a, b = before.splitlines(), after.splitlines()
    if not a or not b:
        return {'complete_since_baseline': False, 'overlap_lines': 0, 'new_lines': []}
    matches = []
    for index, line in enumerate(a):
        size = len(a) - index
        if line == b[0] and size <= len(b) and a[index:] == b[:size]:
            matches.append((size, index))
    if not matches:
        return {'complete_since_baseline': False, 'overlap_lines': 0, 'new_lines': []}
    size, dropped = max(matches)
    return {'complete_since_baseline': True, 'overlap_lines': size,
            'old_head_lines_dropped': dropped, 'new_lines': b[size:]}


def planned_rtc_window(runtime, attribution_proved):
    return bool(runtime.get('sysfs_result', {}).get('errno') == 0
                and 1 <= runtime.get('residency_seconds', -1) <= 20
                and runtime.get('rtc_irq_delta') == 1 and attribution_proved)


def qualify(directory):
    directory = Path(directory)
    names = ['runtime-result.json', 'before-private.json', 'after-private.json',
             'sample-before-private.json', 'sample-after-private.json', 'pm-trace-private.txt',
             'native-allowance-before-private.json', 'native-allowance-after-private.json',
             'dmesg-before-private.txt', 'dmesg-after-private.txt', 'worker.py', 'fetch-stdout-private.json']
    original = {name: (directory / name).read_bytes() for name in names}
    runtime = json.loads(original['runtime-result.json'])
    first, last = [json.loads(original[name]) for name in ['before-private.json', 'after-private.json']]
    first_sample, last_sample = [json.loads(original[name]) for name in ['sample-before-private.json', 'sample-after-private.json']]
    text = original['pm-trace-private.txt'].decode()
    # Use only the already-tested, inert candidate parser/health functions.
    path = ROOT / 'pm-worker-candidate/worker.py'
    worker = types.ModuleType('offline_reviewed_worker'); worker.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), worker.__dict__)
    trace = worker.audit_trace(text)
    phase_pattern = re.compile(r'\s(\d+\.\d+): suspend_resume: (\w+)\[[^\]]+\] (begin|end)')
    phases = [{'phase': m[2], 'edge': m[3], 't': float(m[1])} for m in phase_pattern.finditer(text)]

    def phase(name, edge):
        rows = [p['t'] for p in phases if p['phase'] == name and p['edge'] == edge]
        if len(rows) != 1:
            raise ValueError('phase missing/ambiguous: ' + name + '/' + edge)
        return rows[0]

    log = ordered_log_tail(original['dmesg-before-private.txt'].decode(), original['dmesg-after-private.txt'].decode())
    new_text = '\n'.join(log['new_lines'])
    ends = re.findall(r'device_pm_callback_end: (\S+) (\S+), err=(-?\d+)', text)
    charger = [r for r in trace['callbacks'] if r['device'] == '0-005c' and r['ops'] and r['phase'] == 'suspend']
    config = lambda s: {k: v for k, v in s['registers'].items() if k != '13'}
    allowances = [json.loads(original[name]) for name in ['native-allowance-before-private.json', 'native-allowance-after-private.json']]
    delta = runtime.get('suspend_stats_delta', {})
    restoration = {'target_callbacks_and_order': trace['passed'],
                   'all_retained_callback_ends_error_zero': bool(ends) and all(int(e[2]) == 0 for e in ends),
                   'same_boot': first['boot_id'] == last['boot_id'] and runtime.get('same_boot') is True,
                   'same_driver_and_release': first['driver'] == last['driver'] == 'samurai-mp2650' and first['release'] == last['release'],
                   'charger_configuration_restored': config(first) == config(last),
                   'native_allowance_preserved': allowances[0] == allowances[1] and type(allowances[1].get('ua')) is int and allowances[1]['ua'] >= 50000,
                   'suspend_stats_success_no_failures': delta.get('success') == 1 and delta.get('fail') == 0 and all(v == 0 for k, v in delta.items() if k.startswith('failed_')),
                   'fresh_post_charge_sample': worker.healthy(last_sample),
                   'camera_and_four_services_preserved': first['camera_pm'] == last['camera_pm'] and first['m2m'] == last['m2m'] and worker.services(first) == worker.services(last),
                   'taint_zero': first['taint'] == last['taint'] == '0',
                   'new_log_interval_retained': log['complete_since_baseline'],
                   'no_recorded_new_target_faults': log['complete_since_baseline'] and all(x not in new_text for x in worker.FAULTS)}
    before_delay = phase('dpm_prepare', 'begin') - phase('suspend_enter', 'end')
    result = {'scope': 'qualified offline r5 audit; original evidence unchanged',
              'passed': False, 'planned_15_second_rtc_s2idle_passed': planned_rtc_window(runtime, False),
              'classification': 'planned_rtc_wakeup_failed_despite_post_resume_restoration',
              'raw_runtime_passed_preserved': runtime.get('runtime_passed'),
              'worker_exited_in_fetch': json.loads(original['fetch-stdout-private.json']).get('alive') is False,
              'measured_residency_seconds': runtime['residency_seconds'],
              'measured_boottime_seconds': runtime['boottime_seconds'],
              'measured_monotonic_seconds': runtime['monotonic_seconds'],
              'rtc_irq_delta': runtime['rtc_irq_delta'], 'rtc_causal_attribution_proved': False,
              'rtc_attribution_limitation': 'No alarm-expiry IRQ timestamp or pm_wakeup_irq was captured. Counter +1 cannot prove the RTC caused this late resume.',
              'duration_within_15_second_plan_and_5_second_tolerance': 1 <= runtime['residency_seconds'] <= 20,
              'pre_device_callback_delay_seconds': before_delay,
              'freeze_processes_seconds': phase('freeze_processes', 'end') - phase('freeze_processes', 'begin'),
              'kernel_sync_seconds': phase('sync_filesystems', 'end') - phase('sync_filesystems', 'begin'),
              'charger_suspend_start_after_delay': bool(charger and charger[0]['start'] > phase('dpm_prepare', 'begin')),
              'charger_suspend_callback_seconds': charger[0]['end'] - charger[0]['start'] if charger else None,
              'root_cause_proved': False,
              'source_region': 'suspend_devices_and_enter before dpm_suspend_start: platform_suspend_begin/console_suspend_all; no function-level timing to isolate an inner cause',
              'post_resume_restoration_checks': restoration,
              'post_resume_restoration_observed': all(restoration.values()),
              'retained_callback_ends': len(ends), 'target_trace_audit': trace,
              'log_interval': {k: v for k, v in log.items() if k != 'new_lines'},
              'new_log_lines': len(log['new_lines']),
              'pre_sample_age_ms': first_sample['age_ms'],
              'pre_sample_would_pass_new_freshness_gate': worker.healthy(first_sample),
              'auditor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'trace_parser_worker_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'inputs_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in original.items()}}
    assert all((directory / name).read_bytes() == data for name, data in original.items())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = qualify(args.directory)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['passed', 'classification', 'measured_residency_seconds',
                                                  'pre_device_callback_delay_seconds', 'post_resume_restoration_observed']}))
