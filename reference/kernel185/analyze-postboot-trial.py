"""Recheck independent HCI/MGMT discovery evidence and the powered RTC round."""
from pathlib import Path
import json
import re

root = Path('/var/lib/samurai')
source = Path('/var/lib/samurai/k185-tools/analyze-scans.py').read_text()
source = source.replace("for name in ['before-v2', 'after']:", "for name in ['postresume']:")
source = source.replace("root / 'k185-load/scan-comparison.json'", "root / 'k185-scan-postresume/scan-validation.json'")
# Reuse exactly the original MGMT/HCI and key checks, retaining zero error expectation.
exec(compile(source, 'reused-independent-scan-verifier', 'exec'))
folder = root / 'k185-scan-after-suspend/powered-suspend'
pm = json.loads((folder / 'validation.json').read_text())
assert pm['suspend_and_rtc_resume_passed'] and pm['same_loaded_module']
assert pm['bluetooth_before']['powered'] and pm['bluetooth_after']['powered']
assert pm['bluetooth_before']['connected_devices'] == pm['bluetooth_after']['connected_devices'] == 0
trace = (folder / 'pm-trace-private.txt').read_text()
ends = [line for line in trace.splitlines() if 'device_pm_callback_end:' in line]
assert ends
errors = [int(re.search(r'err=(-?\d+)', line)[1]) for line in ends]
assert all(error == 0 for error in errors)
qca_ends = [line for line in ends if 'qca' in line.lower()]
pm['callback_end_records'] = len(ends)
pm['callback_error_records'] = sum(error != 0 for error in errors)
pm['qca_callback_end_records'] = len(qca_ends)
pm['post_resume_three_transport_scans_passed'] = True
pm['post_resume_scan_pending'] = False
pm['scan_immediately_after_resume_passed'] = False
pm['initial_combined_trial_passed'] = False
pm['initial_failure'] = 'Wi-Fi not associated at 5180 MHz at the immediate two-second health check'
pm['wifi_recovered_without_manual_rebind_or_reconnect'] = True
pm['wifi_recovery_latency_measured'] = False
pm['delayed_post_resume_scan_used'] = True
(folder / 'validation-reviewed.json').write_text(json.dumps(pm, indent=2) + '\n')
print(json.dumps(pm))
