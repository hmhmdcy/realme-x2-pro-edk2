"""Check target-specific TMC10 evidence and save a scoped local commit."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel411')

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out

reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['knee','aec','chain']}
assert all(r['passed'] for r in reports.values())
for n in ['model-r1','prior-source-r1','aec-r1']:assert not json.loads((HERE/(n+'-validation.json')).read_text())['passed']
assert reports['knee']['cases']==2643 and reports['knee']['invalid_cases']==33
assert reports['knee']['actual_target_knees_and_percentage_verified'] and reports['knee']['logf_and_powf_are_host_libm_not_target_bionic']
assert reports['aec']['cases']==837 and reports['aec']['invalid_cases']==11
assert reports['aec']['all_eleven_region_fields_checked'] and reports['aec']['full_target_interpolation_knees_and_sampling_executed']
assert reports['chain']['successful_boost_chain_cases']==reports['chain']['native_typed_lut_cases']==2596
assert reports['chain']['compared_lut_bytes']==1329152 and reports['chain']['different_bytes']==0
assert reports['chain']['prior_1301_chain_different_records']==58 and reports['chain']['prior_1301_chain_different_bytes']==4044
for name in ['knee','aec']:
    assert all(r['passed'] and r['different_bytes']==0 for r in reports[name]['architectures'])
for report in reports.values():
    for item in report['current_source_hashes']:
        assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
assert state['tmc10_knee_generation_target_verified'] and state['tmc10_aec_interpolation_target_verified']
assert not state['tmc10_knee_policy_matches_pinned_source'] and not state['full_ltm_numeric_math_complete']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['reference/kernel410/libipa/tmc10.cpp','reference/kernel410/README.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through410-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix=='.md':assert not check.link_errors(ROOT,str(relative)),(relative,check.link_errors(ROOT,str(relative)))
    if relative.suffix=='.py':ast.parse((ROOT/relative).read_text())
    if relative.suffix=='.json':json.loads((ROOT/relative).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==411 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_tmc10_knee_target_verified'] and d['ipe_ltm_tmc10_aec_interpolation_verified']
    assert not d['ipe_ltm_tmc_version_mix_policy_verified'] and not d['ipe_ltm_full_factory_numeric_math_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation=dict(stage=411,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,
    tested_numeric_sources_current_hashes_match=True,kernel406_clean_unchanged=True,
    actual_target_knees_percentage_and_complete_aec_checked=True,target_math_provider_scope_explicit=True,
    source_version_difference_corrected_and_prior_failure_retained=True,prior_changed_lut_bytes_recorded=True,
    initial_knee_layout_and_aec_input_abi_failures_retained=True,source_packers_and_native_typed_luts_checked=True,
    disabled_roots_and_supplier_variant_scope_preserved=True,no_new_device_epoch_claimed=True,
    private_sources_tables_asm_outputs_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:410 extraction,sampling,ADRC chain and scoped local checkpoint',
    current_goal_turn_classification='progress:411 actual target knee correction,complete TMC10 AEC interpolation and downstream LUT verification',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel411/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='8a21da3c76a2dd3b0e4a536394412de6ddb03911','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
    target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: match target TMC10 knees and implement AEC interpolation','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=411,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
