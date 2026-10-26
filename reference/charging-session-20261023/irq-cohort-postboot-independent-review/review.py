"""Static/hash/AST review only. Do not import or run author collectors/tests."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
AUTHOR=REF/'charging-oem-audit-20261023/irq-cohort-postboot-readonly'
COHORT=REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def funcs(p):
    text=p.read_text()
    return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}


def consts(p):
    result={}
    for n in ast.parse(p.read_text()).body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            try:result[n.targets[0].id]=ast.literal_eval(n.value)
            except (ValueError,TypeError):
                if n.targets[0].id=='COHORT_EXPECTED_MANIFEST':result[n.targets[0].id]=json.loads(n.value.args[0].value)
    return result


assert sha(AUTHOR/'delivery.json')=='6efc3e39bbef834f1e29926b876e2d8378afce3434c197b3eefc8b4bfddd81a3'
delivery=json.loads((AUTHOR/'delivery.json').read_text())
for n,row in delivery['files'].items():
    assert sha(AUTHOR/n)==row['sha256'] and (AUTHOR/n).stat().st_size==row['bytes'],n
old=AUTHOR/'history/revision-1'
old_delivery=json.loads((old/'delivery.json').read_text())
for n,row in old_delivery['files'].items():assert sha(old/n)==row['sha256'],n
before,after=funcs(old/'device.py'),funcs(AUTHOR/'device.py')
changed=[n for n in before if before[n]!=after[n]]
assert changed==['parse_interrupts']
helper=funcs(AUTHOR/'irq-evidence.py')
assert all(after[n]==body for n,body in helper.items())
for n in ['device.py','irq-evidence.py']:
    old_text=(old/n).read_text()
    assert old_text.replace(before['parse_interrupts'],after['parse_interrupts'],1)==(AUTHOR/n).read_text(),n
reuse=json.loads((AUTHOR/'source-reuse.json').read_text())
original=AUTHOR.parent/'image502-postboot-readonly/device.py'
assert sha(original)==reuse['source_device_sha256']=='8da495324ea341714f193d8406ec860a93733971599f2c50e8c51c7a88ba4ab2'
orig=funcs(original)
assert len(reuse['unchanged_functions'])==21
for n,h in reuse['unchanged_functions'].items():
    assert orig[n]==after[n] and hashlib.sha256(after[n].encode()).hexdigest()==h,n
assert reuse['helper_sha256']==sha(AUTHOR/'irq-evidence.py')
old_test=json.loads((old/'test-result.json').read_text())
new_test=json.loads((AUTHOR/'shared-actions-test-result.json').read_text())
aggregate=json.loads((AUTHOR/'test-result.json').read_text())
assert old_test['passed'] and old_test['affected_cases']==27
for n,h in old_test['tested_files'].items():assert sha(old/n)==h,n
assert new_test['passed'] and new_test['new_affected_cases']==10 and new_test['default_check_returncode']==0
assert new_test['original_27_reused_not_rerun'] and aggregate['original_27_reused_not_rerun']
assert aggregate['original_27_receipt_sha256']==new_test['original_27_receipt_sha256']==sha(old/'test-result.json')
assert aggregate['new_test_receipt_sha256']==sha(AUTHOR/'shared-actions-test-result.json')
for n,h in new_test['files'].items():assert sha(AUTHOR/n)==h,n
counter=HERE/'shared-action-result.json'
assert new_test['review_counterexample_sha256']==sha(counter)=='603ddb01b8c9df0a821668e1751e8ebc51d03b583755e496afc9d50890c73fe5'
assert json.loads(counter.read_text())['function_sha256']==hashlib.sha256(before['parse_interrupts'].encode()).hexdigest()
initial=AUTHOR/'history/revision-2-initial-metadata'
assert new_test['executed_test_script_sha256']==sha(initial/'test-shared-actions.py')
assert new_test['current_test_script_sha256']==sha(AUTHOR/'test-shared-actions.py')
assert new_test['metadata_correction']['original_receipt_sha256']==sha(initial/'shared-actions-test-result.json')
executed=(initial/'test-shared-actions.py').read_text()
current=(AUTHOR/'test-shared-actions.py').read_text()
assert executed[:executed.index('    result =')]==current[:current.index('    result =')]
delta=list(difflib.unified_diff(executed.splitlines(),current.splitlines()))
removed=[l for l in delta if l.startswith('-') and not l.startswith('---')]
added=[l for l in delta if l.startswith('+') and not l.startswith('+++')]
assert len(removed)==len(added)==1
assert 'review_counterexample_sha256' in removed[0] and 'review_counterexample_sha256' in added[0]
cohort=json.loads((COHORT/'cohort-manifest.json').read_text())
manifest=json.loads((COHORT/'manifest.json').read_text())
constants=consts(AUTHOR/'device.py')
assert constants['COHORT_EXPECTED_MANIFEST']==manifest
assert constants['COHORT_MANIFEST']==sha(COHORT/'manifest.json')==cohort['new_manifest_sha256']
assert constants['IRQ_BOOT']==cohort['required_carriers']['boot']['sha256']
assert constants['LOGDUMP502']==cohort['required_carriers']['logdump']['sha256']
assert constants['IMAGE502']==cohort['Image502_sha256']
for n,item in cohort['modules'].items():
    assert constants['COHORT_NOTES'][n.replace('-','_')]==item['new']['resident_note_sha256']
    assert manifest['modules'][n]['sha256']==item['new']['sha256']
assert constants['COHORT_NOTES']['samurai_mp2650']==cohort['unchanged_charger_identity']['resident_note_sha256']
# Static read-only boundary and the unchanged collection/check flows were read.
text=(AUTHOR/'device.py').read_text()
assert all(t not in text for t in ['/dev/mem','O_RDWR','PROT_WRITE'])
assert 'args.execute' in after['main'] and 'if sys.flags.optimize:raise RuntimeError' in after['main']
assert "'physical_delivery_accepted': False" in helper['delta']
assert "'IRQ_delivery_or_icon_latency_accepted': False" in helper['check_postboot']
report=dict(schema='samurai-irq-cohort-postboot-independent-review-v1',status='accepted-limited-component-scope',
            reviewed_delivery_sha256=sha(AUTHOR/'delivery.json'),delivery_files_verified=len(delivery['files']),
            reviewed_sources={n:sha(AUTHOR/n) for n in ['device.py','irq-evidence.py']},
            original_21_function_bodies_exact=True,R1_finding='shared action first/middle skipped despite valid pair',
            R1_finding_receipt_sha256=sha(counter),R1_finding_resolved_in_R2=True,changed_function_only=changed,
            R2_ten_new_cases_and_default_receipt_verified=True,old_27_receipt_reused_not_rerun=True,
            metadata_correction=dict(actual_counterexample_hash_verified=True,original_bad_receipt_preserved=True,
                                     executed_and_current_runner_distinguished=True,assertion_bodies_unchanged=True),
            static_findings_checked=['exact cohort manifest structure and boot/FAT/Image502 pins',
              'new disk/live notes for USB and protection; charger retained',
              'actual supply native OF binding and sole provider plus exact 5 properties',
              'two unique named IRQ registrations, dynamic Linux IRQ numbers',
              'per-CPU monotonic deltas and CPU hotplug/remap incomparable',
              'registration and count growth never physical delivery/icon-latency acceptance',
              'no CSR/control/service/guard/pointer write or new adoption',
              'host stage/context authentication not implemented; no deployment-ready claim'],
            source_bindings={str(p.relative_to(REF)):sha(p) for p in [AUTHOR/'delivery.json',AUTHOR/'test-result.json',
              AUTHOR/'shared-actions-test-result.json',AUTHOR/'source-reuse.json',COHORT/'delivery.json',COHORT/'cohort-manifest.json',COHORT/'manifest.json']},
            review_operations='read/hash/AST only after R2; one new R1 isolated actual parser counterexample+direction control',
            author_modules_or_entry_or_tests_executed=False,new_R2_cases_rerun=False,old_suite_rerun=False,
            device_SSH_USB_build_SDK_Git=False,physical_acceptance=False,whole_host_deployment_flow_reviewed=False)
(HERE/'review-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],review_sha256=sha(HERE/'review-result.json'),files=len(delivery['files']))))
