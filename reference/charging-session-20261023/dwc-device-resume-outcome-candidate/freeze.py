"""Hash-only final checks and delivery, no source generation or test invocation."""
from pathlib import Path
import hashlib, json, re, sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sys.flags.optimize:
    raise RuntimeError('nonoptimized freeze required')
source = json.loads((HERE/'source-result.json').read_bytes())
test = json.loads((HERE/'test-result.json').read_bytes())
assert source['passed'] and test['passed']
for name, digest in source['source_inputs'].items():
    assert sha(REF/name) == digest, name
for name, digest in source['candidate_sha256'].items():
    assert sha(HERE/name) == digest, name
for name, digest in test['files'].items():
    assert sha(HERE/name) == digest, name
header = (HERE/'core.h').read_text()
pm = header[header.index('/* power management interface */'):header.index('#if IS_ENABLED(CONFIG_USB_DWC3_ULPI)')]
gadget_branch, host_branch = pm.split('#else', 1)
assert gadget_branch.startswith('/* power management interface */\n#if !IS_ENABLED(CONFIG_USB_DWC3_HOST)')
assert 'void dwc3_gadget_resume_result(' in gadget_branch
assert 'static inline void dwc3_gadget_resume_result(' in host_branch
assert host_branch.count('#endif') == 1
gadget = (HERE/'gadget.c').read_text()
assert 'EXPORT_SYMBOL' not in gadget[gadget.index('void dwc3_gadget_resume_result'):]
assert not re.search(r'\b(?:for|while)\s*\(', gadget[gadget.index('static void dwc3_gadget_resume_device'):])
contract = dict(schema='samurai-dwc-device-resume-outcome-internal-v1',
    implemented=True, core_consumer_implemented=False, same_Image_internal_only=True,
    function='void dwc3_gadget_resume_result(struct dwc3 *, struct dwc3_device_resume_result *)',
    fields=['primary','recovery','requested','recovery_attempted','operation_completed','detail'],
    recovery_detail_fields=['stage','start_seq','end_seq','pending','reconnected'],
    result_requires_non_NULL_caller_owned_stack=True,
    caller_retains_bound_controller_and_powered_core_PHY=True,
    pending_is_publication_snapshot_not_producer_exclusion=True,
    reconnected_is_actual_soft_connect_zero_not_physical_enumeration=True,
    HOST_guard_matches_existing_PM_interface=True,
    legacy_primary_OTG_exports_unchanged=True, persistent_dwc_fields_added=False,
    future_PM_abort_and_safe_unwind_proved=False,
    gadget_sha256=sha(HERE/'gadget.c'), header_sha256=sha(HERE/'core.h'),
    test_result_sha256=sha(HERE/'test-result.json'))
(HERE/'interface-contract.json').write_text(json.dumps(contract,indent=2)+'\n',newline='\n')
names=['README.md','prepare.py','freeze.py','gadget.c','core.h','device-resume-outcome.patch',
       'actual-functions.inc','host-stubs.inc','previous-resume.inc','source-result.json',
       'test-outcome.c','test-host-stub.c','test-outcome.py','test-result.json','interface-contract.json']
delivery=dict(schema=1,passed=True,frozen=True,scope='stack-only internal DEVICE resume outcome; core unchanged',
    files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in names},
    source_inputs=source['source_inputs'], new_outcome_cases=18, HOST_stub_cases=1,
    legacy_differential_scenarios=16, all_new_fixture_children_terminal_zero=True,
    old_7_15_13_24_20_126_suites_rerun=False, kernel_object_or_Image_built=False,
    core_consumer_added=False, PM_unwind_complete=False, deployed=False,
    device_SSH_USB_storage_helper_SDK_Git_used=False)
(HERE/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n',newline='\n')
print(json.dumps(dict(delivery_sha256=sha(HERE/'delivery.json'),
    contract_sha256=sha(HERE/'interface-contract.json'),files=len(names))))
