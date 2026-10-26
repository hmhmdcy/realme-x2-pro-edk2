"""Check relevant complete-function evidence and save a scoped local checkpoint."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel416')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['input','execute']}
i=reports['input'];e=reports['execute']
assert i['passed'] and i['cases']==1002 and i['invalid_cases']==4 and i['binding_cases']==16
assert i['nonfinite_target_results_atomically_rejected']==2 and i['earlier_global_version_table_claim_retracted']
assert i['module88_exposure_time_ratio_module92_sensitivity_ratio']
assert all(r['passed'] and r['different_bytes']==0 and r['compared_bytes']==20120 for r in i['architectures'])
assert e['passed'] and e['complete_execute_calls']==154 and e['ordinary_mode_contexts']==14 and e['physical_sensor_variants']==4
assert e['calculated_requests']==72 and e['module_version_differs_from_retained_property_version_cases']==12
assert e['complete_original_execute_entry']=='0x383728' and e['original_returned_success_each_time']
assert not e['phone_accessed'] and not e['product_request_integration'] and not e['android_runtime_metadata_observed']
assert all(r['passed'] and r['different_bytes']==0 and r['compared_bytes']==1316392 for r in e['architectures'])
for report in reports.values():
    for item in report['current_source_hashes']:assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert state['tmc_ipe_request_version_global_table_claim_retracted'] and state['tmc_ipe_input_stack_base_verified']
assert state['tmc_ipe_request_version_binding_verified'] and state['tmc11_hdr_input_field_identities_verified'] and state['tmc11_full_execute_offline_verified']
assert not state['tmc_runtime_metadata_actually_observed'] and not state['tmc_runtime_version_selection_verified']
assert not state['full_ltm_numeric_math_complete'] and not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md',
    'archive/NEXT-SESSION-through415-2026-10-21.md','reference/kernel415/README.md',
    'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',
    'linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
    if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
    if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
    if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==416 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert d['ipe_ltm_tmc_ipe_request_version_binding_verified'] and d['ipe_ltm_tmc11_full_execute_offline_verified']
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert not d['ipe_ltm_tmc_version_mix_policy_verified'] and not d['ipe_ltm_runtime_submission_enabled'] and not d['ipe_ltm_product_default_enabled']
validation=dict(stage=416,changed_document_links_syntax_json_checked=True,entrypoint_limits_kept=True,
    tested_sources_current_hashes_match=True,maintained406_kernel_clean_unchanged=True,
    prior_wrong_global_version_table_retracted_and_true_stack_base_proven=True,
    actual_adrc_version_binding_and_aec_hdr_ratios_verified=True,
    whole_swtmc11_execute_return_and_continuous_state_match_verified=True,
    synthetic_uid_enable_missing_property_and_immutable_histogram_scope_explicit=True,
    retained_adrc_not_misrepresented_as_fresh_hardware_data=True,
    next_priority_runnable_candidate_request_and_device_loop=True,
    actual_android_product_and_hardware_not_claimed=True,private_arrays_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:415 target dependency/version,ADRC wire cache and LTM gate',
    current_goal_turn_classification='progress:416 corrected true IPE binding,AEC HDR domains,whole SWTMC11 Execute and composed continuous steps',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
selected.append(Path('reference/kernel416/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='638aaf982c8c113ff7aca0835cc09d19b239f58b','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
    target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: verify full SWTMC11 execution and correct IPE input binding','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=416,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
