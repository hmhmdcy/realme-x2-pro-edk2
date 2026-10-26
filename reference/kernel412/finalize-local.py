"""Check TMC11 factory/mode/model2 evidence and save a scoped local checkpoint."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel412')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['factory-tmc11','mode-tmc','sampling','chain']}
assert all(r['passed'] for r in reports.values())
for n in ['sampling-r1','source-helper-r1']:assert not json.loads((HERE/(n+'-validation.json')).read_text())['passed']
assert reports['factory-tmc11']['roots']==68 and reports['factory-tmc11']['regions']==198
assert reports['mode-tmc']['physical_cameras']==4 and reports['mode-tmc']['physical_mode_contexts']==14 and reports['mode-tmc']['module_queries']==28
assert reports['mode-tmc']['android_runtime_metadata_not_observed']
assert reports['sampling']['cases']==1192 and reports['sampling']['target_tmc11_knee_generation_and_histogram_generation_not_executed']
assert reports['sampling']['source_pchip_different_bytes']==7 and reports['sampling']['source_contrast_different_bytes']==16692
assert all(r['passed'] and r['different_bytes']==0 for r in reports['sampling']['architectures'])
assert reports['chain']['native_typed_lut_cases']==1026 and reports['chain']['rejected_finite_subunity_cases']==166
assert reports['chain']['compared_lut_bytes']==525312 and reports['chain']['different_bytes']==0
for name in ['sampling','chain']:
    for item in reports[name]['current_source_hashes']:
        assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
assert state['tmc11_factory_tree_extraction_verified'] and state['tmc11_ltm_normalization_pchip_contrast_target_verified']
assert not state['tmc11_knee_generation_target_verified'] and not state['tmc_runtime_version_selection_verified'] and not state['full_ltm_numeric_math_complete']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through411-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix=='.md':assert not check.link_errors(ROOT,str(relative)),(relative,check.link_errors(ROOT,str(relative)))
    if relative.suffix=='.py':ast.parse((ROOT/relative).read_text())
    if relative.suffix=='.json':json.loads((ROOT/relative).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==412 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_tmc11_factory_extraction_verified'] and d['ipe_ltm_tmc11_ltm_sampling_verified']
    assert not d['ipe_ltm_tmc11_knee_target_verified'] and not d['ipe_ltm_tmc_version_mix_policy_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation=dict(stage=412,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,
    tested_numeric_sources_current_hashes_match=True,kernel406_clean_unchanged=True,
    complete_factory_tmc11_trees_and_original_mode_selector_checked=True,ordinary_mode_selection_not_claimed_runtime_version=True,
    target_normalization_pchip_contrast_and_numeric_lut_chain_checked=True,target_knee_and_histogram_generation_kept_unverified=True,
    source_helper_differences_and_invalid_fixture_failure_retained=True,finite_subunity_chain_rejections_not_clamped=True,
    disabled_roots_supplier_variant_and_private_table_scope_preserved=True,no_new_device_epoch_claimed=True,
    private_sources_tables_asm_outputs_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:411 actual target TMC10 knee correction,AEC interpolation and local checkpoint',
    current_goal_turn_classification='progress:412 complete TMC11 factory trees/mode binding,target model2 sampling and ADRC/native LUT chain',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel412/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='35629ba39de3add08578b917e9a3c799ffa0a325','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
    target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover TMC11 modes and match target PCHIP contrast sampling','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=412,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
