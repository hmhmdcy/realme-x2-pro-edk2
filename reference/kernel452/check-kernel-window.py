"""Re-audit the retained full kernel read against the trusted monotonic boundary."""
from pathlib import Path
import hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('mount449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mount.mounted_build()
p=Path('/mnt/e/edk2-samurai-out/kernel452')
owner_path=p.parent/'charging-management-20261023/pm-r5-recovery/snapshot-private.json'
current_path=p/'final-health-and-kernel-private.json'
owner=json.loads(owner_path.read_text());current=json.loads(current_path.read_text())
health_path=HERE.parent/'charging-management-20261023/charging-health.py'
spec=importlib.util.spec_from_file_location('read_only_health_audit',health_path)
health=importlib.util.module_from_spec(spec);spec.loader.exec_module(health)
summary=health.audit(current['health'])
assert summary==current['health_audit'] and summary['passed']
assert owner['result']['worker_exited'] and owner['result']['terminal'] and owner['result']['charging_healthy']
assert summary['manifest_sha256']==owner['result']['manifest_sha256']
assert summary['native_allowance_after']==owner['result']['native_allowance_ua']
boundary=float(owner['monotonic']);now=float(current['monotonic'])
assert 0<boundary<now
def timestamped(text):
 rows=[]
 for line in text.splitlines():
  match=re.search(r'\[\s*(\d+\.\d+)\]',line)
  if match:rows.append((float(match[1]),line))
 return rows
before=timestamped(owner['dmesg']);after=timestamped(current['dmesg'])
assert before and after and min(t for t,l in after)<boundary
assert max(t for t,l in after)<=now+1
assert before[-1][1] in current['dmesg'], 'Trusted prior tail must still be retained'
region=[line for stamp,line in after if stamp>=boundary]
assert region
fault=re.compile(r'Unhandled|IOMMU.*[Ff]ault|arm-smmu.*[Ff]ault|SError|BUG:|WARNING:|Oops:|[Tt]ranslation fault|watchdog received|CCI error|Stream stop failed:|Missing SOF tag')
faults=[line for line in region if fault.search(line)]
loss=[line for line in region if re.search(r'messages suppressed|messages dropped|printk.*dropped|Lost \d+ messages',line,re.I)]
assert not faults and not loss
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
report=dict(stage=452,scope='Combined 451 and 452 camera window after trusted charging-owner recovery',owner_snapshot_sha256=sha(owner_path),current_read_sha256=sha(current_path),health_auditor_sha256=sha(health_path),boundary_clock='CLOCK_MONOTONIC',kernel_timestamp_clock='MONOTONIC',prior_kernel_tail_still_retained=True,retention_covers_boundary=True,new_kernel_lines=len(region),specified_new_faults=0,no_log_loss_indicators=True,taint=summary['taint'],charging_health_passed=True,charging_samples=summary['sample_count'],manifest_and_native_allowance_match_owner=True,formal_limits_unchanged=True,camera_and_four_services_unchanged_during_final_health=True,original_boottime_filter_valid=False,original_one_byte_logs_rejected_as_fault_evidence=True,no_camera_rerun_for_supplement=True,phone_accessed_by_this_auditor=False,passed=True)
(HERE/'kernel-window-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
