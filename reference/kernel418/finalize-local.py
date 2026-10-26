"""Save a scoped local checkpoint after source, hardware and restoration checks."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['build','ipe','source','runtime-build','runtime','hardware','current-state']}
assert all(r.get('passed',r.get('state',{}).get('passed')) for r in reports.values())
assert reports['ipe']['cases']==37 and reports['ipe']['three_completion_orders']==6
hardware=reports['hardware'];assert hardware['typed_iq_wrapper_frames']==16 and hardware['all_active_pixels_equal_prior_fixed_diagnostics']
assert hardware['camera_pipeline_request_frames']==81 and hardware['kernel_candidate_completed']==97 and hardware['kernel_candidate_jobs']==99
assert hardware['wrapper_cancelled_callbacks']==4 and hardware['kernel_cancelled_jobs']==2
assert not hardware['candidate_nonzero_iq_ipa_algorithm_integrated'] and hardware['candidate_automatic_iq_payloads_still_bypass']
runtime=reports['runtime'];s=runtime['state'];health=reports['current-state']
assert s['terminal'] and not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
assert s['normal395_restored'] and s['new_unexpected_fault_count']==0 and s['taint']==512
assert len(s['candidate_captures'])==7 and s['candidate_captures']['isolated']['actual_isolation_verified']
assert health['m2m']['jobs']==health['m2m']['completed']==health['m2m']['direct_completed']==48
assert not health['transaction_live'] and health['taint']==512 and not any(health['clocks'].values())
assert all(v=='suspended' for v in health['camera_pm'].values())
assert all(v['state']=='disabled' and v['users']==0 for v in health['rails'].values())
assert not json.loads((HERE/'runtime-r1-validation.json').read_text())['state']['passed']
state=json.loads((HERE/'source-state.json').read_text());tree=storage.candidate()/'src/libcamera-v0.7.2'
for item in state['source_hashes']:assert hashlib.sha256((tree/item['path']).read_bytes()).hexdigest()==item['sha256']
assert hashlib.sha256((tree/'output/src/libcamera/libcamera.so.0.7.2').read_bytes()).hexdigest()==reports['runtime-build']['library_sha256']
source=storage.mount.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['kernel_commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md',
    'archive/NEXT-SESSION-through417-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',
    'linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
    if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
    if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
    if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for p,limit in check.load_manifest(ROOT)['size_limits'].items():
    if p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limit
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==418
    assert d['ipe_media_request_iq_libcamera_integrated'] and not d['ipe_media_request_iq_ipa_parameter_generation_integrated']
    assert d['maintained_commit']==state['kernel_commit'] and not d['ipe_ltm_runtime_submission_enabled'] and d['device_current_taint']==512
validation=dict(stage=418,changed_document_links_syntax_json_checked=True,entrypoint_limits_kept=True,
    actual_compiled_and_hardware_tested_library_source_hashes_match=True,public_patch_zero_fuzz_reproduction_verified=True,
    request_wrapper_and_camera_pipeline_hardware_verified=True,automatic_ipa_payload_bypass_scope_explicit=True,
    model_and_actual_wrapper_cancellation_counts_not_confused_with_kernel_jobs=True,
    failed_test_layout_attempt_retained=True,known417_warning_taint_preserved_without_new418_faults=True,
    all_transactions_terminal_and_formal_stack_restored=True,private_coefficients_not_exported=True,
    previous_goal_turn_classification='progress:417 typed per-frame Media Request kernel IQ and real pixel equality',
    current_goal_turn_classification='progress:418 actual libcamera request/control endpoint and three-way ownership verified through nonzero pixels,81 camera request frames and cancellation',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel418/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='51ae0fd56d9e3880d4c906920ba40084c7c9e219','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
    target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: connect libcamera IPE media requests and verify completion ownership','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=418,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=True,last_device_stage=418,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
