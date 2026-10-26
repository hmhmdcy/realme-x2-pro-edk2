"""Bind the narrow actual pair/postboot source and author fake-boundary receipts."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
PAIR=REF/'charging-session-20261023/gauge-image501-fastboot-pair-candidate'
POST=REF/'charging-management-20261023/image501-postboot-readonly'
OLD=REF/'charging-session-20261023/eud-fastboot-operator-r2'
OLDPOST=REF/'charging-oem-audit-20261023/eud-postboot-readonly-candidate-r3'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def functions(path):
    source=path.read_text()
    return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
pair=functions(PAIR/'fastboot-operator.py');old=functions(OLD/'fastboot-operator.py')
same_pair=['command','process_info','fetch','prior_terminal','claim_action']
assert all(pair[n]==old[n] for n in same_pair)
post=functions(POST/'device.py');oldpost=functions(OLDPOST/'device.py')
same_post=['block_fact','check_install','check_camera','check_producers','check_services','healthy_charge_mode','module_fact']
assert all(post[n]==oldpost[n] for n in same_post)
assert post['check_charging']==oldpost['check_charging'].replace('==100','==500')
pins=json.loads((PAIR/'activation-pins.json').read_bytes())
for name,digest in pins.items():assert sha(REF/'charging-session-20261023/gauge-image501-activation-candidate'/name)==digest
records={}
for name,path,source,field in [('pair',PAIR/'test-result.json',PAIR/'fastboot-operator.py','operator_sha256'),
 ('context',PAIR/'context-test-result.json',PAIR/'fastboot-operator.py','operator_sha256'),
 ('postboot',POST/'test-result.json',POST/'device.py','device_sha256')]:
    raw=json.loads(path.read_bytes());assert raw['passed'] and raw[field]==sha(source)
    test={'pair':'test-pair.py','context':'test-context.py','postboot':'test-delta.py'}[name]
    assert raw['test_sha256']==sha(path.parent/test)
    records[name]={'receipt_sha256':sha(path),'source_sha256':sha(source),'case_count':raw['case_count'],'test_sha256':raw['test_sha256']}
assert records['pair']['case_count']==6 and records['context']['case_count']==7 and records['postboot']['case_count']==9
assert json.loads((POST/'test-result.json').read_bytes())['payload_sha256']==sha(POST/'payload.py')
assert "int(r['charger']['input_current_limit'])==500000" in post['check_gauge']
result={'passed_limited_review':True,'new_blocker_found':False,'scope':'narrow pair/unknown/reboot plus new Image501 current/500 acceptance; static source and already-executed author fake-boundary receipts',
 'files':{str(p.relative_to(REF)):{'sha256':sha(p)} for p in [PAIR/'fastboot-operator.py',PAIR/'activation-pins.json',POST/'device.py',POST/'payload.py']},
 'receipts':records,'byte_equal_old_pair_functions':same_pair,'byte_equal_old_postboot_functions':same_post,
 'activation_pins_actual_bytes_match':True,'both_partition_geometry_and_all_members_checked_before_any_flash':True,
 'explicit_logdump_then_boot_and_no_automatic_reboot':True,'partial_or_unknown_pair_blocks_reboot':True,
 'latest_successful_exact_pair_required_for_its_own_once_reboot':True,'full_explicit_original_pair_before_original_reboot':True,
 'new_boot_exact_501_and_optin_Y_unique_cmdline_required':True,'CURRENT_NOW_and_AVG_independently_valid_required':True,
 'SDP_MaxPower_native_source_and_hardware_input_all_500_required':True,'whole_both_partitions_exact_required':True,
 'static_tests_rerun_by_reviewer':False,'device_USB_SSH_SDK_Git_used':False,'runtime_pass_claimed':False}
(HERE/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed_limited_review':True,'review_sha256':sha(HERE/'review.json'),'receipt_cases':[6,7,9]}))
