"""Offline hashes/diffs only; no transport or collector import."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parents[1]/'charging-ui-audit-20261023/icon-capture-r7-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'migration-test-result.json').read_bytes())
assert test['passed'] is True and test['tests_run']==12
assert all(sha(HERE/n)==h for n,h in test['tested_files'].items())
assert all((HERE/n).read_bytes()==(OLD/n).read_bytes() for n in ['worker.py','audit.py','baseline-test-result.json'])
diff=''.join(difflib.unified_diff((OLD/'launcher.py').read_text().splitlines(True),(HERE/'launcher.py').read_text().splitlines(True),fromfile='R7/launcher.py',tofile='R8-EUD-off/launcher.py'))
diff+=''.join(difflib.unified_diff([], (HERE/'capture-entry.py').read_text().splitlines(True),fromfile='/dev/null',tofile='R8-EUD-off/capture-entry.py'))
(HERE/'migration.diff').write_text(diff)
result=dict(schema='charging-icon-r8-eud-off-candidate-v1',offline_preparation_passed=True,frozen=True,
 manifest_sha256=test['manifest_sha256'],identity_pins_sha256=sha(HERE/'identity-pins.json'),
 launcher_sha256=sha(HERE/'launcher.py'),capture_entry_sha256=sha(HERE/'capture-entry.py'),
 tests=dict(affected_groups_passed=12,receipt_sha256=sha(HERE/'migration-test-result.json'),
 historical_collector_cases=32,historical_R7_migration_cases=8,historical_cases_rerun=False),
 contract=dict(default_action='check-local',deadline_boottime_seconds=300,
 reconnect_settle_seconds=90,host_ready_min_remaining_seconds=130,host_prompt_freshness_seconds=3,
 launch_once_per_transaction=True,unknown_dispatch_status_fetch_only=True,fetch_same_boot_guard_mandatory=True,
 fetch_nonboot_identity_failure_preserves_originals=True,descriptor_or_budget_writes=False,
 missing_attribute_or_ENODATA_preserved=True),
 phone_accessed=False,ssh_executed=False,USB_accessed=False,SDK_invoked=False,Git_invoked=False,build_invoked=False,
 physical_acceptance=False,pixel_latency_measured=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
names=['worker.py','audit.py','baseline-test-result.json','capture-entry.py','launcher.py','identity-pins.json',
 'prepare.py','test-migration.py','run-migration-tests.py','migration-test-result.json','migration.diff','README.md','result.json','freeze.py']
delivery=dict(schema='charging-icon-r8-eud-off-delivery-v1',frozen=True,files={n:sha(HERE/n) for n in names})
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
print(json.dumps(dict(launcher=result['launcher_sha256'],entry=result['capture_entry_sha256'],test=sha(HERE/'migration-test-result.json'),result=sha(HERE/'result.json'),delivery=sha(HERE/'delivery.json'))))
