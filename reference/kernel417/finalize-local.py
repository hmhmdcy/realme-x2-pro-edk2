"""Check relevant evidence and save a scoped, private-data-free local commit."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel417')

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out

reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['intree-build','params','client-build','runtime','pixels','current-state']}
assert all(r.get('passed',r.get('state',{}).get('passed')) for r in reports.values())
assert reports['intree-build']['attempt']==3 and not reports['intree-build']['diagnostics']
assert reports['params']['cases']==28 and reports['params']['asan_ubsan']
assert reports['pixels']['frames']==16 and reports['pixels']['all_active_pixels_equal_prior_fixed_diagnostic_outputs']
assert all(r['different_bytes']==0 for r in reports['pixels']['rows'])
runtime=reports['runtime'];s=runtime['state'];health=reports['current-state']
assert s['terminal'] and not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
assert s['normal395_restored'] and s['new_unexpected_fault_count']==0 and s['taint']==512
assert not s['collector_result']['captured'] and not s['collector_result']['timeout']
assert len(s['captures'])==4 and sum(r['frames'] for r in s['captures'].values())==48
assert health['m2m']['completed']==health['m2m']['direct_completed']==49 and health['taint']==512
assert not health['transaction_live'] and all(v=='suspended' for v in health['camera_pm'].values())
assert not any(health['clocks'].values()) and all(r['state']=='disabled' and r['users']==0 for r in health['rails'].values())
assert not reports['pixels']['libcamera_request_integration'] and not reports['pixels']['automatic_factory_tuning']
for n in ['runtime-r1','runtime-r2','runtime-r3']:assert not json.loads((HERE/(n+'-validation.json')).read_text())['state']['passed']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
for item in state['source_hashes']:assert hashlib.sha256((source/item['path']).read_bytes()).hexdigest()==item['sha256']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md',
    'archive/NEXT-SESSION-through416-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json',
    'linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
    if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
    if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
    if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for p,limit in check.load_manifest(ROOT)['size_limits'].items():
    if p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limit,(p,(ROOT/p).stat().st_size,limit)
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==417
    assert d['maintained_commit']==state['commit'] and d['device_current_taint']==512
    assert d['ipe_media_request_iq_hardware_verified'] and not d['ipe_media_request_iq_libcamera_integrated']
    assert not d['ipe_ltm_runtime_submission_enabled'] and not d['ipe_ltm_product_default_enabled']
validation=dict(stage=417,changed_document_links_syntax_json_checked=True,entrypoint_limits_kept=True,
    tested_source_hashes_and_committed_clean_tree_match=True,
    media_request_compound_control_hardware_pixels_verified=True,known_failed_warning_and_taint_preserved=True,
    fixed_reference_not_automatic_factory_tuning=True,all_transactions_terminal_and_formal_stack_restored=True,
    standard_libcamera_iq_connection_still_pending=True,private_arrays_not_exported=True,
    previous_goal_turn_classification='progress:416 full TMC11 offline flow and corrected IPE binding',
    current_goal_turn_classification='progress:417 per-frame typed Media Request IQ on real ISP with pixel equality and restored four-camera operation',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel417/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='4e3e5c9f83d2a9bea37c290e8e16b2c0bd36849b','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
    target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: attach typed IPE IQ to media requests and verify hardware pixels','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=417,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=True,last_device_stage=417,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
