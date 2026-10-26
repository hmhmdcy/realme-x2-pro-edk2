"""Bind retained source and timeline, without executing collectors or tests."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
UI = HERE.parent
R8 = REF / 'charging-session-20261023/r8-source-integration'
SUPPLY = R8 / 'kernel-sources/drivers/power/supply'
G = REF / 'charging-oem-audit-20261023/gauge-current-samurai-candidate'
UP = UI / 'phosh-connection-source-r8/release-files/upower'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
delivery = read(R8 / 'delivery.json')['files']
paths = [SUPPLY / n for n in ['samurai-mp2650.c', 'samurai-usb-input.c', 'samurai-gauge-protection.c',
                             'mp2650-core.h', 'charging-notify.h', 'gauge-i2c.h', 'oem-full-cycle.h']]
for p in paths: assert sha(p) == delivery[str(p.relative_to(R8)).replace('\\', '/')]
baseline, instant = (G / 'baseline-bq27xxx_battery.c').read_text(), (G / 'bq27xxx_battery.c').read_text()
callback = r'static void bq27xxx_external_power_changed\(.*?\n\}'
assert re.search(callback, baseline, re.S)[0] == re.search(callback, instant, re.S)[0]
assert 'HZ / 2' in re.search(callback, instant, re.S)[0]
assert sha(G / 'bq27xxx_battery.c') == '0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'
kernel = read(UI / 'kernel-sources.json')
assert sha(UI / 'kernel-power_supply_core.c') == kernel['power_supply_core.c']['sha256']
binding = read(UI / 'phosh-connection-source-r8/binding-result.json')
upower_paths = ['src/up-daemon.c', 'src/up-device.c', 'src/up-device-battery.c',
                'src/linux/up-enumerator-udev.c', 'src/linux/up-device-supply.c', 'src/linux/up-device-supply-battery.c']
for name in upower_paths:
    assert sha(UP / name) == binding['unchanged_audited_source']['upower/' + name]['sha256']
constants = (UP / 'src/up-constants.h').read_text()
assert re.search(r'UP_DAEMON_UNKNOWN_TIMEOUT\s+1\b', constants)
assert re.search(r'UP_DAEMON_UNKNOWN_POLL_TIME\s+5\b', constants)
timeline_path = UI / 'remaining-icon-delay-r8/timeline.json'
timeline = read(timeline_path)
assert timeline['source_capture_sha256'] == '57d98e04d5a987d4598e552779133fb4b5f492bedfe7042860517c71a79abe5e'
paths += [G / 'bq27xxx_battery.c', G / 'baseline-bq27xxx_battery.c', UI / 'kernel-power_supply_core.c',
          UP / 'src/up-constants.h', timeline_path] + [UP / name for name in upower_paths]
result = {
    'scope': 'bottom-only attach latency and notification plan; UI addition/build/review cancelled and not deployed',
    'sources': {str(p.relative_to(REF)).replace('\\', '/'): sha(p) for p in paths},
    'capture': 'old363 genuine physical cycle; existing501 capture001 has no observed edge',
    'fixed_wait_identified': 'BQ external_power_changed HZ/2, unchanged in instant501',
    'proposed_change_not_implemented': 'only strict existing instant Samuari profile callback queue delay0; original delay for other profiles',
    'existing_post_apply_REG13_and_BQ_STATUS_signature_kept': True,
    'MP_supplier_notifier_already_immediate': True,
    'power_supply_notifier_precedes_uevent': True,
    'UPower_line_event_idle_refresh_and_1second_5second_fastpoll': True,
    'MAC_nominal_query_wait_count_per_online_safe_collect': 11,
    'MAC_nominal_wait_ms_range': [11, 16.5],
    'physical_converter_and_gauge_transition_time_not_separated_by_old_capture': True,
    'three_second_or_501_edge_improvement_accepted': False,
    'root_owns_USB_IRQ_followup': True,
    'no_Ph osh_UPower_kernel_source_changed'.replace(' ', ''): True,
    'device_SDK_build_Git_test_or_new_collector_operations': False,
    'readme_sha256': sha(HERE / 'README.md')
}
(HERE / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'review_sha256': sha(HERE / 'review.json'), 'proposal_implemented': False}))
