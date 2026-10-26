"""Check the installed channel and save only its public checkpoint paths."""
from pathlib import Path
import ast,hashlib,importlib.util,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['package-source','package-build','package-artifact','install','hardware','current-state']}
assert all(r['passed'] for r in reports.values())
i=reports['install'];h=reports['current-state'];hw=reports['hardware']
assert i['installed'] and i['driver_pair_installed'] and i['terminal'] and not any(i[k] for k in ['worker_live','client_live','collector_live'])
assert i['new_fault_count']==0 and i['taint_after']==512 and not i['rollback']
assert hw['total_new_ipe_completed']==93 and hw['camera_suite_completed']==81 and hw['ordinary_user_pipewire_frames']==12
assert hw['typed_request_path_logged_for_each_camera_dual_and_isolated'] and not hw['automatic_ipa_nonzero_iq_generation']
assert h['m2m']['jobs']==h['m2m']['completed']==h['m2m']['direct_completed']==93 and not h['transaction_live']
assert h['production_driver_pair_disk_and_loaded_notes_match'] and h['test_parameters_absent']
candidate=storage.candidate();tree=candidate/'src/libcamera-v0.7.2'
source=json.loads((HERE.parent/'kernel418/source-state.json').read_text())
for item in source['source_hashes']:assert hashlib.sha256((tree/item['path']).read_bytes()).hexdigest()==item['sha256']
for package in ['libcamera','samurai-camera-config']:
 recipe=HERE/'recipes'/package;lock=json.loads((recipe/'source-lock.json').read_text());assert lock['installed'] and not lock['candidate_only']
 for name,digest in lock['source_files_sha256'].items():assert hashlib.sha256((recipe/name).read_bytes()).hexdigest()==digest,(package,name)
 if package=='libcamera':shutil.copyfile(recipe/'source-lock.json',candidate/'source-lock.json')
 else:shutil.copyfile(recipe/'source-lock.json',candidate.parent/'samurai-camera-config420-r31/source-lock.json')
 # The same README has one less ancestor in linux-port/packages.
 p=ROOT/'linux-port/packages'/package/'README.md';p.write_text(p.read_text().replace('../../../../reference/','../../../reference/'))
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through419-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
selected += [Path('linux-port/packages/libcamera')/p for p in ['APKBUILD','source-lock.json','0041-camss-ipe-request.patch','README.md']]
selected += [Path('linux-port/packages/samurai-camera-config')/p for p in ['APKBUILD','source-lock.json','README.md']]
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for p,limit in check.load_manifest(ROOT)['size_limits'].items():
 if p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limit
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==420 and d['in_progress_installed']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
 assert d['current_icp_core_source_stage']==d['current_icp_adapter_source_stage']==419
 assert d['ipe_media_request_iq_libcamera_integrated'] and not d['ipe_media_request_iq_ipa_parameter_generation_integrated']
validation=dict(stage=420,changed_document_links_syntax_json_checked=True,source_recipe_hashes_match_built_and_tested_channel=True,
 installed_driver_and_packages_verified=True,typed_request_path_not_just_legacy_fallback_verified=True,
 all_feature_packages_preserved_and_six_ipa_unchanged=True,automatic_ipa_generation_still_incomplete=True,
 default_paths_four_cameras_raw_isolation_and_ordinary_pipewire_verified=True,
 all_transactions_terminal_services_restored_resources_released=True,private_data_not_packaged=True,
 known417_taint_and_original419_worker_failure_preserved=True,rollback_retained_not_claimed_exercised=True,
 previous_goal_turn_classification='no progress: acceleration advice only;revalidated and executed next safe integration action',
 current_goal_turn_classification='progress:installed signed r31/r26 and production419 pair;93 direct frames and real requests=1 across4cameras/dual/isolated,ordinary PipeWire12',
 full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel420/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='de7013b9479636c73855d948d56cd7e9479e611a','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
 target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: install signed per-frame IPE channel and production recovery drivers','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=420,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=True,last_device_stage=420,passed=True)
(host.PRIVATE/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
