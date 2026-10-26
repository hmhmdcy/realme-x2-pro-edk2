"""Validate changed TMC10 evidence and save a scoped local checkpoint."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel410')

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out

reports={name:json.loads((HERE/(name+'-validation.json')).read_text()) for name in ['factory-tmc10','tmc','chain']}
assert all(r['passed'] for r in reports.values())
for name in ['model-r1','tmc-r1']:assert not json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert reports['factory-tmc10']['roots']==5 and reports['factory-tmc10']['regions']==18
assert reports['tmc']['cases']==1301 and reports['tmc']['target_sampler_calls']==1298
assert reports['tmc']['target_sampler_different_bytes']==reports['tmc']['target_mix_different_bytes']==0
assert reports['tmc']['target_knee_generation_not_executed'] and reports['tmc']['powf_is_host_libm_not_target_bionic']
assert all(r['passed'] and r['different_bytes']==0 for r in reports['tmc']['architectures'])
assert reports['chain']['successful_boost_chain_cases']==reports['chain']['native_typed_lut_cases']==1254
assert reports['chain']['compared_lut_bytes']==642048 and reports['chain']['different_bytes']==0
assert reports['chain']['rejected_cases']==47 and reports['chain']['rejected_finite_subunity_gain_cases']==2
assert reports['chain']['qtech_gw1_unbound_supplier_variant_is_numeric_fixture_only']
assert all(r['passed'] for r in reports['chain']['architectures'])
for item in reports['chain']['current_source_hashes']:
    assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
assert state['tmc10_gain_sampling_target_verified'] and state['tmc10_numeric_chain_to_native_lut_verified']
assert not state['tmc10_knee_generation_target_verified'] and not state['full_ltm_numeric_math_complete']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through409-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix=='.md':assert not check.link_errors(ROOT,str(relative)),(relative,check.link_errors(ROOT,str(relative)))
    if relative.suffix=='.py':ast.parse((ROOT/relative).read_text())
    if relative.suffix=='.json':json.loads((ROOT/relative).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==410 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_tmc_gain_sampling_verified'] and d['ipe_ltm_tmc10_numeric_lut_chain_verified']
    assert not d['ipe_ltm_tmc10_knee_target_verified'] and not d['ipe_ltm_tmc_version_mix_policy_verified']
    assert not d['ipe_ltm_full_factory_numeric_math_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation=dict(stage=410,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,
    tested_numeric_sources_current_hashes_match=True,kernel406_clean_unchanged=True,
    source_knee_policy_not_claimed_target_verified=True,target_sampler_and_mix_checked=True,
    target_powf_provider_scope_explicit=True,source_packers_and_native_typed_luts_checked=True,
    initial_abi_and_zero_endpoint_domain_failures_retained=True,supplier_variants_not_claimed_physical_cameras=True,
    disabled_roots_preserved_and_finite_subunity_rejected=True,no_new_device_epoch_claimed=True,
    private_sources_tables_asm_outputs_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:409 target ADRC conversion blend LUT and signed packing correction',
    current_goal_turn_classification='progress:410 factory TMC10 extraction,source knee policy,target sampling and ADRC-LUT numeric chain',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel410/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='e27543357b3c436e164ad1a2027da59defb24d50','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
    target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover TMC10 sampling and connect offline ADRC LUT chain','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=410,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
