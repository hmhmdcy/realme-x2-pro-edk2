"""Validate TMC11 generation evidence and save a scoped local checkpoint."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel413')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['gamma-default','generation','chain']}
assert all(r['passed'] for r in reports.values())
for n in ['model-r1','model-r2','generation-r1']:assert not json.loads((HERE/(n+'-validation.json')).read_text())['passed']
assert hashlib.sha256((P/'target-default-gamma-private.bin').read_bytes()).hexdigest()==reports['gamma-default']['compiled_default_gamma_sha256']
assert reports['generation']['cases']==156 and reports['generation']['factory_region_aliases']==198 and reports['generation']['distinct_factory_regions']==31
assert reports['generation']['finite_target_results']==154 and reports['generation']['nonfinite_target_result_cases']==2
assert reports['generation']['coefficients_and_histogram_generated_by_actual_target_not_fixture']
assert reports['generation']['finite_dark_knee_quotient_not_clipped_to_second_anchor']
assert all(r['passed'] and r['different_bytes']==0 and r['compared_bytes']==1393056 for r in reports['generation']['architectures'])
assert reports['chain']['native_typed_lut_cases']==142 and reports['chain']['rejected_finite_subunity_cases']==12 and reports['chain']['rejected_nonfinite_generation_cases']==2
assert reports['chain']['compared_lut_bytes']==72704 and reports['chain']['different_bytes']==0
for name in ['generation','chain']:
    for item in reports[name]['current_source_hashes']:
        assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
assert state['tmc11_knee_generation_target_verified'] and state['tmc11_histogram_generation_target_verified']
assert not state['tmc11_drc_hdr_aec_interpolation_verified'] and not state['tmc_runtime_version_selection_verified'] and not state['full_ltm_numeric_math_complete']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through412-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix=='.md':assert not check.link_errors(ROOT,str(relative)),(relative,check.link_errors(ROOT,str(relative)))
    if relative.suffix=='.py':ast.parse((ROOT/relative).read_text())
    if relative.suffix=='.json':json.loads((ROOT/relative).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==413 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_tmc11_knee_target_verified'] and d['ipe_ltm_tmc11_histogram_generation_verified']
    assert not d['ipe_ltm_tmc11_drc_hdr_aec_interpolation_verified'] and not d['ipe_ltm_tmc_version_mix_policy_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation=dict(stage=413,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,
    tested_numeric_sources_current_hashes_match=True,kernel406_clean_unchanged=True,
    actual_target_generation_not_source_knee_fixture_checked=True,all198_region_aliases_covered_by31_distinct_parameters=True,
    compiled_gamma_default_and_controlled_gamma_scope_explicit=True,absent_histogram_byte_fill_not_claimed_float_unity=True,
    two_initial_abi_failures_and_dark_knee_source_difference_retained=True,nonfinite_and_subunity_rejections_not_clamped=True,
    generated_state_to_target_sampling_adrc_and_native_lut_chain_checked=True,
    dynamic_interpolation_runtime_metadata_and_device_scope_kept_unverified=True,private_tables_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:412 complete TMC11 factory trees/mode binding and model2 sampling/LUT chain',
    current_goal_turn_classification='progress:413 actual TMC11 histogram/knee/coefficient/percentage/contrast generation and generated-state LUT chain',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel413/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='e9679e31946414fe27fb142a0b0e87c166aa84d7','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
    target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: match target TMC11 histogram and knee generation','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=413,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
