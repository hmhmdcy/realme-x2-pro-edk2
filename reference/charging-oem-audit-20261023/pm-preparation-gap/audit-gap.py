"""Read-only calculation over the recovered r5 originals; never alters them."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import re

root = Path(__file__).resolve().parent
raw = Path('E:/edk2-samurai-out/charging-management-20261023/pm-r5')
trace_path, dmesg_path = raw / 'pm-trace-private.txt', raw / 'dmesg-after-private.txt'
trace, dmesg = trace_path.read_text(), dmesg_path.read_text()
runtime = json.loads((raw / 'runtime-result.json').read_text())
def trace_time(pattern):
    m = re.search(r'(\d+\.\d+): ' + pattern, trace)
    assert m, pattern
    return Decimal(m[1])
freeze = trace_time(r'suspend_resume: freeze_processes\[0\] end')
prepare = trace_time(r'suspend_resume: dpm_prepare\[2\] begin')
console = Decimal(re.search(r'\[\s*(\d+\.\d+)\] printk: Suspending console\(s\)', dmesg)[1])
charger_start = trace_time(r'device_pm_callback_start: samurai-mp2650 [^\n]*driver \[suspend\]')
charger_end_match = re.search(r'(\d+\.\d+): device_pm_callback_end: samurai-mp2650 [^\n]*err=0',
                             trace[trace.index(str(charger_start)):])
assert charger_end_match
charger_end = Decimal(charger_end_match[1])
files = (trace_path, dmesg_path, raw / 'dmesg-before-private.txt',
         raw / 'worker.py', raw / 'runtime-result.json')
out = {
    'freeze_end_mono': str(freeze), 'console_message_mono': str(console),
    'dpm_prepare_begin_mono': str(prepare),
    'freeze_to_prepare_seconds': str(prepare - freeze),
    'console_message_to_prepare_seconds': str(prepare - console),
    'charger_driver_suspend_begin_mono': str(charger_start),
    'charger_driver_suspend_end_mono': str(charger_end),
    'charger_driver_suspend_seconds': str(charger_end - charger_start),
    'raw_residency_seconds': runtime['residency_seconds'],
    'raw_monotonic_seconds': runtime['monotonic_seconds'],
    'raw_boottime_seconds': runtime['boottime_seconds'],
    'raw_rtc_irq_delta': runtime['rtc_irq_delta'],
    'raw_runtime_passed': runtime['runtime_passed'],
    'raw_criteria_check_planned_15_seconds': False,
    'planned_15_second_wakeup_verified': False,
    'rtc_irq_timestamp_available': False,
    'alarm_target_or_time_remaining_saved': False,
    'source_manifest': 'source-manifest.json',
    'raw_files_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    'phone_accessed': False, 'raw_modified': False,
}
(root / 'gap-audit.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2))
