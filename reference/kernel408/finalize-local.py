"""Validate changed evidence and save the temporal adaptation locally."""
from pathlib import Path
import ast, hashlib, importlib.util, json, subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=Path('/mnt/e/edk2-samurai-out/kernel408')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
temporal=json.loads((HERE/'temporal-validation.json').read_text())
api=json.loads((HERE/'api-validation.json').read_text())
assert temporal['passed'] and api['passed']
assert temporal['valid_cases']==3931 and temporal['invalid_cases']==47
assert temporal['factory_complete_regions']==2135 and temporal['variant_sequence_updates']==1200
assert all(r['passed'] and not r['different_bytes'] for r in temporal['architectures'])
assert not json.loads((HERE/'model-r1-validation.json').read_text())['passed']
for item in api['sources']:
    assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py')
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
assert state['portable_temporal_primitive_verified'] and not state['full_ltm_numeric_math_complete']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py')
(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['reference/kernel407/libipa/ltm_curves.cpp','reference/kernel407/libipa/ltm_curves.h','reference/kernel407/README.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through407-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix=='.md':assert not check.link_errors(ROOT,str(relative)),(relative,check.link_errors(ROOT,str(relative)))
    if relative.suffix=='.py':ast.parse((ROOT/relative).read_text())
    if relative.suffix=='.json':json.loads((ROOT/relative).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:
    assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for relative in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/relative).read_text())
    assert d['latest_work_stage']==408 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_oem_temporal_primitive_math_verified'] and d['ipe_ltm_curve_phase_order_verified']
    assert not d['ipe_ltm_oem_temporal_upstream_tags_verified'] and not d['ipe_ltm_oem_temporal_hardware_verified']
    assert not d['ipe_ltm_full_factory_numeric_math_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation=dict(stage=408,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,
                current_math_sources_match_final_api_checks=True,maintained_kernel406_clean_unchanged=True,
                target_temporal_math_and_full_curve_phase_state_checked=True,
                original_407_api_all6630_records_preserved=True,
                model_end_boundary_failure_retained=True,raw_upstream_tag_identity_gap_explicit=True,
                global_lifetime_and_product_commit_not_claimed=True,
                offline_sequence_updates_not_camera_frames=True,last_device_stage=406,
                private_original_sources_tables_outputs_not_exported=True,
                previous_goal_turn_classification='progress:407 portable LTM curve primitives and native LUT connection',
                current_goal_turn_classification='progress:408 target Face smoothing state and curve ordering implemented and compared',
                full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n')
selected.append(Path('reference/kernel408/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='c7c9dbc2f0da4dbc801d6ef3bafc2c562e2f8026','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
    target=mirror/relative;data=export.public_bytes(ROOT,relative)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data
    paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: port target face smoothing and preserve pre-attenuation history','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=408,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),
             only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,
             pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
