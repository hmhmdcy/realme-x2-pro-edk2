"""Check the cached MONOTONIC camera log and later physical USB transition."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out')
camera=private/'kernel452/runtime-collected-r2'
worker=(private/'kernel452/diagnostic-prepared-r2/worker.py').read_text()
assert 'start_uptime=time.monotonic()' in worker
assert "start_uptime=float(Path('/proc/uptime').read_text().split()[0])" not in worker
state=json.loads((camera/'state.json').read_text())
log=(camera/'kernel-log-private.txt').read_text()
later=json.loads((private/'kernel459/final-health-after-replug-private.json').read_text())
controller=json.loads((private/'kernel459/runtime-collected-r2/result.json').read_text())
assert state['passed'] and state['new_faults']==[] and state['taint_after']==state['taint_before']==0
lines=log.splitlines();assert lines and log.strip()
stamps=[]
for line in lines:
 match=re.match(r'\[\s*(\d+\.\d+)\]',line);assert match
 stamps.append(float(match[1]))
 assert line in later['dmesg']
assert min(stamps)>=controller['launched_monotonic_ns']/1e9
assert max(stamps)<=controller['ended_monotonic_ns']/1e9<later['monotonic']
fault=re.compile(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|Missing SOF tag')
assert not any(fault.search(line) for line in lines)
assert not re.search(r'messages suppressed|messages dropped|printk.*dropped|Lost \d+ messages',log,re.I)
post=[]
for line in later['dmesg'].splitlines():
 match=re.match(r'\[\s*(\d+\.\d+)\]',line)
 if match and float(match[1])>controller['ended_monotonic_ns']/1e9:post.append(line)
source=[line for line in post if 'samurai-mp2650' in line and 'error=-61' in line]
assert source and later['health_audit']['passed'] is False
assert later['health_audit']['state_counts']['waiting_source']==2
report=dict(stage=459,worker_cutoff_clock='MONOTONIC',camera_window_kernel_lines=len(lines),
 camera_window_kernel_sha256=hashlib.sha256(log.encode()).hexdigest(),
 camera_log_nonempty=True,all_camera_lines_retained_in_later_complete_read=True,
 all_camera_log_timestamps_within_actual_controller_window=True,camera_selected_faults=0,
 camera_log_loss_indicators=0,camera_window_taint=0,
 later_source_enodata_lines=len(source),later_waiting_source_samples=2,later_managed_health_passed=False,
 later_source_change_is_after_terminal_camera_window=True,
 usb_replug_context_from_explicit_charging_thread=True,source_change_cause_fixed=False,
 phone_read_or_write_performed_by_this_checker=False,passed=True)
(HERE/'kernel-r2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
