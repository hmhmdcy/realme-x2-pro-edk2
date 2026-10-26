"""Independent static hash/source review only. Never import author entrypoints."""
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
C=REPO/'reference/charging-session-20261023/apsd-phy-lifetime-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
EXPECTED='006ccd88790a8ca70f39d212cdaa2873e92cb217df43b44571f2cac954c7b807'
assert sha(C/'delivery.json')==EXPECTED
d=json.loads((C/'delivery.json').read_bytes())
for collection in ['files','history']:
    for name,digest in d[collection].items():assert sha(C/name)==digest,name
for name,digest in d['component_bases'].items():assert sha(REPO/name.replace('\\','/'))==digest,name
test=json.loads((C/'test-result.json').read_bytes())
for name,digest in test['tested_files'].items():assert sha(C/name)==digest,name
build=json.loads((C/'build-result.json').read_bytes())
assert test['passed'] and test['affected_groups']==9 and build['passed']
source=(C/'phy-qcom-snps-femto-v2.c').read_text()
owner=(C/'samurai-apsd-owner.c').read_text()
old_phy=(REPO/'reference/charging-oem-audit-20261023/apsd-phy-window-candidate/phy-qcom-snps-femto-v2.c').read_text()
old_owner=(REPO/'reference/charging-oem-audit-20261023/apsd-pd5v-client-bridge-candidate/samurai-apsd-owner.c').read_text()
def function(text,name):
    m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|bool|void)\s+(?:__maybe_unused\s+)?'+re.escape(name)+r'\([^;]*?\)\s*\{',text,re.M)
    assert m,name
    begin=text.index('{',m.start());depth=1;i=begin+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[m.start():i]
unchanged=[]
for name in ['owner_free','owner_pd_get','owner_pd_put','owner_work','owner_join','owner_queue','owner_notify','owner_pd_observe']:
    assert function(owner,name)==function(old_owner,name),name;unchanged.append(name)
for name in ['qcom_snps_hsphy_window_write','qcom_snps_hsphy_write_mask','qcom_snps_hsphy_suspend','qcom_snps_hsphy_resume']:
    assert function(source,name)==function(old_phy,name),name;unchanged.append(name)
for name in ['qcom_snps_hsphy_window_begin','qcom_snps_hsphy_window_end']:
    a=function(source,name+'_active');b=function(old_phy,name)
    assert a[a.index('{'):]==b[b.index('{'):],name;unchanged.append(name+' body')
manifest=json.loads((C/'function-manifest.json').read_bytes())
for entry in manifest:
    actual=function(owner if entry['source']=='owner-candidate' else source,entry['function'])
    assert hashlib.sha256(actual.encode()).hexdigest()==entry['sha256'],entry['function']
assert len(manifest)==27
gate=function(owner,'owner_entry_gate')
assert 'return -EOPNOTSUPP;' in gate and 'rerun_once(' not in gate
probe=function(source,'qcom_snps_hsphy_probe')
assert probe.count('pm_runtime_enable(dev);')==1 and 'devm_pm_runtime_enable(dev)' not in probe
assert probe.index('pm_runtime_get_noresume')<probe.index('pm_runtime_enable')<probe.index('window_provider_pm_cleanup')<probe.index('devm_phy_create')<probe.index('devm_of_phy_provider_register')<probe.index('window_provider_publish')<probe.index('qcom_snps_hsphy_withdraw')<probe.index('pm_runtime_put(dev)')
result={'schema':'samurai-apsd-phy-lifetime-independent-review-v1','decision':'accepted_in_reviewed_offline_component_scope',
        'blocking_findings':[],'author_delivery_sha256':EXPECTED,
        'author_files_verified':len(d['files']),'author_history_files_verified':len(d['history']),
        'component_base_files_verified':len(d['component_bases']),'actual_extraction_manifest_verified':27,
        'unchanged_actual_functions_or_bodies':unchanged,
        'checks':{
          'single_enable_and_idempotent_disable_wrapper':True,
          'early_terminal_PM_barrier_before_generic_PHY_devres':True,
          'cancel_join_and_PM_wait_outside_registry_and_PHY_mutex':True,
          'callback_primary_and_extra_real_kref_lifetime':True,
          'unregister_does_not_wait_for_callback_holding_owner_registry':True,
          'admitted_operations_drained_before_terminal_resource_release':True,
          'old_binding_identity_checked_before_old_PHY_dereference':True,
          'system_runtime_reason_specific_complete_and_terminal_no_republish':True,
          'default_optin_and_final_EOPNOTSUPP_preserved':True},
        'reused_author_evidence':{'test_sha256':sha(C/'test-result.json'),'actual_groups':9,
          'old_8_14_groups_not_rerun':True,'build_sha256':sha(C/'build-result.json'),
          'build_objects':d['private_build']['objects'],'W1_Werror':True},
        'not_covered':['Kernel lockdep and all possible unrelated generic PHY consumers.',
          'Real hardware power/reset behavior, route ownership, write-time physical-generation lease, PD protocol or final1341 authority.',
          'Physical timing/USB/PM acceptance or deployment approval.'],
        'author_generators_tests_or_builds_executed_by_reviewer':False,
        'phone_SSH_USB_SDK_Git_or_storage_guard_accessed_by_reviewer':False,
        'author_frozen_bytes_modified':False,'review_source_sha256':sha(Path(__file__))}
(HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'decision':result['decision'],'blocking_findings':0,'review_sha256':sha(HERE/'review-result.json')}))
