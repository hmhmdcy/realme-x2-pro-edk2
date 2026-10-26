"""Final local source/receipt binding only. No queries/builds are dispatched."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
test=json.loads((HERE/'test-result.json').read_bytes());build=json.loads((HERE/'build-result.json').read_bytes())
assert test['passed'] and test['actual']['actual_function_cases']==21 and build['passed'] and build['shared_original_inputs_unchanged']
for n,d in test['tested_files'].items():assert sha(HERE/n)==d
for n,d in build['source_sha256'].items():assert sha(HERE/n)==d
for row in json.loads((HERE/'source-pins.json').read_bytes()).values():assert sha(Path(row['path']))==row['sha256']
def fn(s,name):
 m=re.search(r'^static (?:inline )?(?:int|void|ssize_t|unsigned int) (?:__init |__exit )?'+name+r'\([^;]*?\)\s*\{',s,re.M);assert m,name
 end=s.index('{',m.start())+1;level=1
 while level:level+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[m.start():end]
base=REF/'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply'
same={}
for file,names in {'gauge-protocol.h':['sm_mac_data_size','sm_le16','sm_le32','sm_gauge_protection_state'],
 'gauge-i2c.h':['sm_gauge_word_locked'],
 'samurai-gauge-protection.c':['sm_protection_read','sm_protection_get','protection_state_show','sm_protection_put','sm_protection_probe','sm_protection_init','sm_protection_exit']}.items():
 old,new=(base/file).read_text(),(HERE/file).read_text()
 for name in names:
  value=fn(new,name);assert value==fn(old,name),(file,name);same[file+'::'+name]=hashlib.sha256(value.encode()).hexdigest()
files={p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='delivery.json'}
result={'status':'offline-actual-functions-and-private-object-passed-not-linked-loaded-or-queried',
 'files':files,'unchanged_actual_normal_functions':same,'affected_actual_function_cases':21,
 'six_real_packets_replayed':6,'new_status_packets_are_synthetic':True,'old149_and_other_suites_rerun':False,
 'object_sha256':build['object_sha256'],'future_module_to_replace':'samurai-gauge-protection',
 'new_ko_or_deployment_manifest_created':False,'new2719_semantics_or_TCA_health_policy_changed':False,
 'default_new_query_IO':False,'device_USB_SSH_ADB_SDK_Git_accessed':False}
(HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'delivery_sha256':sha(HERE/'delivery.json'),'provider_sha256':sha(HERE/'samurai-gauge-protection.c'),
 'test_receipt_sha256':sha(HERE/'test-result.json'),'build_receipt_sha256':sha(HERE/'build-result.json')}))
