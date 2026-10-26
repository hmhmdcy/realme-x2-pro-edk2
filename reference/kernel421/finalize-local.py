"""Keep the real observation boundary and reentry evidence in a scoped commit."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['source','build','signature','history','statistics-reentry','hardware-r1','hardware-r2','current-state']}
assert all(r['passed'] for r in reports.values())
assert [x['cases'] for x in reports['history']['models']]==[22,12] and reports['statistics-reentry']['cases']==11
assert reports['statistics-reentry']['old_order_reproduces_premature_missing_statistics']
assert reports['hardware-r1']['candidate_ipe_frames']==81 and reports['hardware-r2']['candidate_ipe_frames']==41
second=reports['hardware-r2'];assert second['cases'][0]['committed']==12 and second['cases'][1]['metadata_exposure_gain_matches']==28
assert second['cases'][1]['app_metadata_without_statistics_sofs']==[7] and second['cases'][1]['superseded']==1
assert not second['native_in_process_ipa_verified'] and second['native_isolated_ipa_verified']
assert not json.loads((HERE/'hardware-r2-first-check-validation.json').read_text())['passed']
for attempt in ['r1','r2']:
 r=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());assert r['passed'] and r['terminal'] and r['formal420_unchanged'] and r['failure'] is None and r.get('cleanup_failure') is None
 assert not any(r[k] for k in ['worker_live','client_live','collector_live']) and not r['new_fault_count'] and r['taint']==512
h=reports['current-state'];assert h['m2m']['completed']==h['m2m']['jobs']==239 and not h['transaction_live'] and h['source_clean']
assert h['production_driver_pair_disk_and_loaded_notes_match'] and h['test_parameters_absent']
s=json.loads((HERE/'source-state.json').read_text());assert s['private_ipa_version']==2 and not s['installed'] and not s['automatic_ipe_numeric_generation']
assert s['statistics_published_before_ipa_parameter_call'] and not s['post_fix_hardware_pending'] and not s['numerical_tmc_history_integrated']
tree=storage.candidate()/'src/libcamera-v0.7.2'
for item in s['source_hashes']:assert hashlib.sha256((tree/item['path']).read_bytes()).hexdigest()==item['sha256']
for item in reports['build']['runtime_files']:assert hashlib.sha256((P/item['name']).read_bytes()).hexdigest()==item['sha256']
old=json.loads((P/'manifest-r1-private.json').read_text());new=json.loads((P/'manifest-private.json').read_text())
assert old['normal_files']==new['normal_files'] and old['profiles']==new['profiles'] and old['notes']==new['notes']
for n in ['ipa/ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign','proxy/camss_ipa_proxy']:assert old['payload_sha256'][n]==new['payload_sha256'][n]
assert old['payload_sha256']['lib/libcamera.so.0.7.2']!=new['payload_sha256']['lib/libcamera.so.0.7.2']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through420-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for p,limit in check.load_manifest(ROOT)['size_limits'].items():
 if p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limit
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==421 and not d['in_progress_installed']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
 assert d['ipe_frame_observation_history_hardware_verified'] and not d['ipe_frame_observation_history_installed']
 assert not d['ipe_numeric_tmc_ltm_history_integrated'] and not d['ipe_media_request_iq_ipa_parameter_generation_integrated']
v=dict(stage=421,changed_document_links_syntax_json_checked=True,actual_source_runtime_artifact_hashes_verified=True,
 source_patch_reproduces_candidate=True,owned_same_sof_context_and_aggregate_history_receipts_verified=True,
 observation_history_not_confused_with_numerical_tmc_history=True,default_and_forced_isolated_hardware_verified_native_in_process_not_claimed=True,
 statistics_reentry_counterexample_and_targeted_fix_verified=True,initial_main_pairing_gap_retained=True,
 raw_only_discard_r1_reused_without_rerun=True,real_missing_stats_sof7_separately_counted_no_commit=True,
 offline_checker_failure_retained_and_no_hardware_repeat_for_report_fix=True,
 all_transactions_terminal_formal420_unchanged=True,known417_taint_and419_failure_preserved=True,
 previous_goal_turn_classification='progress:420 production419 driver pair and signedr31/r26 channel installed,93directframes verified',
 current_goal_turn_classification='progress:real sameSOF observations and final receipts;stats publication reentry root cause fixed and main12/12verified,actual out-of-order success safely superseded',
 full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(v,indent=2)+'\n');selected.append(Path('reference/kernel421/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='c48f9ab0d590d4c7c5838a97fe1ce6a107778c41','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
 target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: bind real frame observations and fix statistics publication reentry','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=421,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
