from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel221')
for p in here.glob('*.py'):compile(p.read_text(),str(p),'exec')
source=json.loads((here/'qualcomm-loc-source-validation.json').read_text())
for name,item in source['files'].items():assert hashlib.sha256((private/'loc-upstream'/name).read_bytes()).hexdigest()==item['sha256']
build=json.loads((here/'loc-readonly-build-validation.json').read_text());assert hashlib.sha256((here/'loc-readonly.c').read_bytes()).hexdigest()==build['source_sha256']
query=json.loads((here/'loc-configuration-validation.json').read_text());old=json.loads((here/'loc-configuration-r2-validation.json').read_text())
assert query['program_exit']==0 and query['cleanup']['client_released'] and query['cleanup']['device_closed']
assert [q['message_id'] for q in query['queries']]==[75,191,183,225]
for current,previous in zip(query['queries'],old['queries']):
 assert current['matching_ack'] and all(current[k]==v for k,v in previous.items() if k not in ['indication_before_ack'])
assert all(q['ack_result']==0 and q['indication_status']==0 for q in query['queries'][:3])
assert query['queries'][1]['constellations']==dict(gps=0,glonass=1,beidou=1,qzss=1,galileo=1,navic=None)
assert query['queries'][2]['blacklist_masks']==dict(glonass=0,beidou=0,qzss=0,galileo=0,sbas=None,navic=None,gps=None)
assert query['queries'][3]['ack_error']==57 and query['queries'][3]['ack_error_name']=='WmsInvalidMessageId'
lock=json.loads((repo/'linux-port/packages/libcamera/source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r7'
assert all(hashlib.sha256((repo/'linux-port/packages/libcamera'/name).read_bytes()).hexdigest()==digest for name,digest in lock['source_files_sha256'].items())
assert (repo/'NEXT-SESSION.md').stat().st_size<=6500
health=json.loads((here/'final-health-validation.json').read_text());archive=json.loads((here/'final-evidence-validation.json').read_text())
assert health['taint']==0 and archive['archive_and_all_member_hashes_verified'] and archive['verified_members']==37
r=dict(stage=221,python_sources_compile=len(list(here.glob('*.py'))),qualcomm_source_files_hash_verified=3,native_final_tool_source_exact=True,two_readonly_query_rounds_consistent=True,ack_identity_and_early_indication_handling_verified=True,missing_fields_not_treated_as_zero=True,current_r7_recipe_locks_exact=True,next_session_bytes=(repo/'NEXT-SESSION.md').stat().st_size,full_goal_active=True)
(here/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n')
final=dict(stage=221,new_readonly_diagnostic_evidence=True,device_runtime_unchanged=True,gnss_constellation_disabled_hypothesis_narrowed=True,gnss_rf_fix_not_established=True,cellular_real_business_not_verified=True,current_camera_r7_r2_preserved=True,native_archive_members=37,full_peripheral_goal_still_active=True)
(here/'final-validation.json').write_text(json.dumps(final,indent=2)+'\n');print(json.dumps(r))
