"""Validate target policy/cache evidence and save only relevant local paths."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel415')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
r=json.loads((HERE/'runtime-validation.json').read_text())
assert r['passed'] and r['policy_valid_cases']==733 and r['policy_invalid_cases']==7
assert r['ltm_gate_valid_cases']==1152 and r['ltm_gate_invalid_cases']==3 and r['ltm_own_tmc10_gate_cases']==16
assert r['metadata_valid_cases']==63 and r['metadata_invalid_cases']==1 and r['actual_generation413_metadata_cases']==3
assert not r['runtime_metadata_actually_observed'] and not r['product_request_integration']
assert r['policy_target_providers']=={} and r['metadata_consumer_providers']=={'0x5b1290':51}
counts={'policy':44400,'consumer':18480,'metadata':271360}
assert len(r['architectures'])==6
for row in r['architectures']:assert row['passed'] and row['different_bytes']==0 and row['compared_bytes']==counts[row['component']]
for item in r['current_source_hashes']:assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
primary=json.loads((HERE/'primary-sources.json').read_text());assert len(primary['new_files'])==4
for item in primary['new_files']:assert hashlib.sha256((P/'sources'/Path(item['path']).name).read_bytes()).hexdigest()==item['sha256']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert state['tmc11_target_dependency_version_policy_verified'] and state['tmc_adrc_metadata_cache_copy_verified'] and state['tmc_ltm_version_selection_gate_verified']
assert not state['tmc_ipe_request_version_global_table_owner_verified'] and not state['tmc_runtime_metadata_actually_observed']
assert not state['tmc_runtime_version_selection_verified'] and not state['full_ltm_numeric_math_complete']
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md',
    'archive/NEXT-SESSION-through414-2026-10-21.md','reference/kernel414/README.md',
    'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',
    'linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
    if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
    if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
    if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==415 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert d['ipe_ltm_tmc_target_dependency_version_policy_verified'] and d['ipe_ltm_tmc_adrc_metadata_cache_copy_verified'] and d['ipe_ltm_tmc_ltm_version_gate_verified']
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert not d['ipe_ltm_tmc_version_mix_policy_verified'] and not d['ipe_ltm_runtime_submission_enabled'] and not d['ipe_ltm_product_default_enabled']
validation=dict(stage=415,changed_document_links_syntax_json_checked=True,entrypoint_limits_kept=True,
    tested_sources_current_hashes_match=True,maintained406_kernel_clean_unchanged=True,
    actual_module_dependency_version_and_lock_policy_checked=True,actual_ipe_cache_copy_and_ltm_gate_checked=True,
    cached_and_missing_property_bytes_not_misrepresented_as_fresh_hardware_state=True,
    prior_ispinput112_label_corrected_in_current_and414_readme=True,
    actual_request_version_global_table_owner_unverified=True,android_runtime_version_not_claimed=True,
    source_newer_than_target_and_version_differences_explicit=True,private_arrays_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:414 actual three-layer TMC11 interpolation and dynamic LUT chain',
    current_goal_turn_classification='progress:415 target dependency/version/locks,ADRC cache wire semantics,and LTM selection gate',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
selected.append(Path('reference/kernel415/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='9a057c8df6bd0d389003612e9a67a7310490f1da','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
    target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover target TMC version and ADRC cache policy','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=415,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
