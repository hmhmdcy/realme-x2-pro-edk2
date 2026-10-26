from pathlib import Path
import ast

ref = Path(__file__).parent
s = (ref.parent / 'kernel176' / 'collect-final.py').read_text()
s = s.replace("Path('/var/lib/samurai/k176-final')", "Path('/var/lib/samurai/k177-final')")
s = s.replace('k176-dmic0-ucm176-low24', 'k177-dmic0-ucm177-low24')
s = s.replace('k176-stop', 'k177-stop').replace('k176-desktop', 'k177-desktop')
s = s.replace('dict(stage=176,', 'dict(stage=177,')
s = s.replace("'/tmp/k176-all-private.tar.gz'", "'/tmp/k177-all-private.tar.gz'")
s = s.replace(".glob('k176*')", ".glob('k177*')")
marker = "report = dict(stage=177,"
addition = '''
pm_cases = []
callback_results = []
for case in ['idle', 'active']:
    root = Path('/var/lib/samurai/k177-suspend-' + case)
    pm = json.loads((root / 'validation.json').read_text())
    assert pm['suspend_and_rtc_resume_passed']
    if case == 'active':
        assert pm['active_duplex_survived']
    trace = (root / 'pm-trace-private.txt').read_text()
    all_ends = re.findall(r'device_pm_callback_end: (.*?), err=(-?\\d+)', trace)
    assert all(int(err) == 0 for name, err in all_ends)
    relevant = {}
    for kind, name in [('card', 'samurai-audio sound'), ('codec', 'wcd934x-codec '),
                       ('mfd', 'wcd934x-slim '), ('ngd', 'qcom,slim-ngd qcom,slim-ngd.1')]:
        phases = re.findall(r'device_pm_callback_start: ' + re.escape(name) + r'[^\\n]*\\[(suspend|resume)\\]', trace)
        assert 'suspend' in phases and 'resume' in phases, (case, kind, phases)
        ends = [int(err) for device, err in all_ends if device.startswith(name)]
        assert ends and all(err == 0 for err in ends)
        relevant[kind] = dict(suspend_seen=True, resume_seen=True, callback_end_results=ends)
    callback_results.append(dict(case=case, relevant_callbacks=relevant, all_pm_callback_end_errors_zero=True,
                                 total_callback_end_events=len(all_ends)))
    pm_cases.append(dict(case=case, residency_seconds=pm['suspend_residency_seconds'],
                         success_delta=pm['suspend_stats_delta']['success'], fail_delta=pm['suspend_stats_delta']['fail'],
                         rtc_alarm_irq_delta=pm['rtc_alarm_irq_delta'], sysfs_errno=pm['sysfs_result']['errno']))
assert int(Path('/sys/power/suspend_stats/success').read_text()) == 2
assert int(Path('/sys/power/suspend_stats/fail').read_text()) == 0
assert not Path('/sys/class/rtc/rtc0/wakealarm').read_text().strip()
assert not Path('/sys/kernel/tracing/instances/k177-pm').exists()
non_audio = dict(usb_hs_phy_not_in_l2=log.count('HS-PHY not in L2'),
                 wifi_invalid_frequency=log.count('chan info: invalid frequency'),
                 wifi_authentication_denied=log.count('denied authentication'))
wlan_state = Path('/sys/class/net/wlan0/operstate').read_text().strip()
'''
assert marker in s
s = s.replace(marker, addition + marker)
s = s.replace('completed_codec_rebinds=2,', 'reprobe_results_belong_to_prior_stage176=True, completed_codec_rebinds=2,')
s = s.replace('physical_headset_not_available_or_tested=True,',
              'system_s2idle_cases=pm_cases, power_callback_validation=callback_results, suspend_stats_success=2, suspend_stats_fail=0,\n              active_desktop_duplex_survived=True, rtc_alarm_cleared=True, temporary_pm_trace_instance_removed=True,\n              non_audio_log_observations=non_audio, wlan_operstate=wlan_state, physical_headset_not_available_or_tested=True,')
s = s.replace('calibrated_audio_quality_cold_boot_ssr_and_system_suspend_not_verified=True',
              'calibrated_audio_quality_cold_boot_ssr_and_long_term_pm_not_verified=True,\n              platform_exposes_s2idle_only_and_no_deep_str=True, uninterrupted_audio_through_sleep_not_verified=True')
ast.parse(s)
(ref / 'collect-final.py').write_text(s)
print('FINAL177_COLLECTOR_PREPARED')
