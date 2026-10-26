"""Validate relevant evidence and save a scoped local414 checkpoint."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel414')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['tree','dynamic-chain']}
tree=reports['tree'];chain=reports['dynamic-chain']
assert tree['passed'] and tree['cases']==2846 and tree['factory_roots']==68 and tree['invalid_cases']==15
assert tree['factory_trigger_cases']==2524 and tree['synthetic_multilevel_cases']==322
assert tree['target_providers']=={'0x5b1250':5692} and tree['maximum_selected_children']==2
assert all(r['passed'] and r['different_bytes']==0 and r['compared_bytes']==514980 for r in tree['architectures'])
assert chain['passed'] and chain['cases']==136 and chain['actual_gap_interpolation_cases']==51
assert chain['chain_success_cases']==131 and chain['native_typed_lut_bytes']==67072
assert chain['rejected_finite_subunity_cases']==5 and chain['rejected_nonfinite_generation_cases']==0
assert all(r['passed'] and r['different_bytes']==0 and r['compared_generation_bytes']==1127712 for r in chain['architectures'])
for report in reports.values():
    for item in report['current_source_hashes']:
        assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert state['tmc11_drc_hdr_aec_interpolation_verified'] and state['tmc11_dynamic_interpolation_to_native_lut_verified']
assert not state['tmc11_hdr_input_field_identities_verified'] and not state['tmc_runtime_version_selection_verified']
assert not state['tmc11_verified'] and not state['full_ltm_numeric_math_complete'] and not state['phone_accessed']
assert not state['installed'] and state['last_device_evidence_stage']==406
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md',
    'archive/NEXT-SESSION-through413-2026-10-21.md','linux-port/camera/deployment-lock.json',
    'linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
    if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
    if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
    if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==414 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert d['ipe_ltm_tmc11_drc_hdr_aec_interpolation_verified'] and d['ipe_ltm_tmc11_dynamic_interpolation_to_native_lut_verified']
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert not d['ipe_ltm_tmc_version_mix_policy_verified'] and not d['ipe_ltm_runtime_submission_enabled'] and not d['ipe_ltm_product_default_enabled']
validation=dict(stage=414,changed_document_links_syntax_json_checked=True,entrypoint_limits_kept=True,
    tested_sources_current_hashes_match=True,maintained406_kernel_clean_unchanged=True,
    original_module_prefix_and_helpers_executed=True,all68_factory_roots_and44_fields_checked=True,
    additional_multilevel_trees_cover_factory_single_drc_hdr_limitation=True,
    actual_hdr2_zero_trigger_scope_explicit=True,upstream_hdr_slot_identities_unverified=True,
    dynamic_tree_output_composed_with_generation_sampling_adrc_and_native_lut=True,
    subunity_rejection_not_clamped=True,runtime_metadata_product_hardware_scope_kept_unverified=True,
    private_trees_and_coefficients_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:413 target TMC11 generation and generated-state LUT chain',
    current_goal_turn_classification='progress:414 target TMC11 three-layer interpolation and dynamic generation-to-native-LUT chain',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
selected.append(Path('reference/kernel414/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='fa743837839ac5549cc51387b45b8fd5f2702839','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
    target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover target TMC11 three-layer interpolation','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=414,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),
    only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,
    pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
