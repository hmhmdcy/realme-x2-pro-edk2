"""Save source and hardware evidence, retaining the original worker failure."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={n:json.loads((HERE/(n+'-validation.json')).read_text()) for n in ['adapter','hook','intree-build','test-intree-build','client-build','fault','current-state']}
assert all(r['passed'] for r in reports.values())
r=json.loads((HERE/'runtime-validation.json').read_text());h=reports['current-state'];f=reports['fault']
assert not r['state']['passed'] and r['state']['case']['passed'] and r['state']['normal395_restored']
assert r['state']['terminal'] and r['state']['failure'] is None and r['state'].get('cleanup_failure') is None
assert not any(r[k] for k in ['worker_live','client_live','collector_live'])
assert f['experiments'][1]['original_worker_false_from_mixed_clock_error_classification_preserved']
assert not h['transaction_live'] and h['m2m']['completed']==48 and h['taint']==512
assert reports['adapter']['cases']==24 and reports['hook']['cases']==7 and not reports['intree-build']['diagnostics']
s=json.loads((HERE/'source-state.json').read_text());mount=module('mount284',HERE.parent/'kernel284/storage.py');source=mount.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==s['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
for item in s['source_hashes']:assert hashlib.sha256((source/item['path']).read_bytes()).hexdigest()==item['sha256']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through418-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for p,limit in check.load_manifest(ROOT)['size_limits'].items():
 if p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limit
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==419 and d['maintained_commit']==s['commit']
 assert d['ipe_media_request_iq_forced_fault_recovery_verified'] and not d['ipe_media_request_iq_ipa_parameter_generation_integrated']
validation=dict(stage=419,changed_documents_links_syntax_json_checked=True,source_clean_committed_and_hash_verified=True,
 actual_typed_request_ack_loss_reset_retirement_recovery_verified=True,original_r2_worker_false_classification_preserved=True,
 strict_saved_log_marker_verifier_passed=True,no_extra_fault_for_report_repair=True,unsafe_quiesce_failure_not_injected=True,
 all_transactions_terminal_formal_restored=True,automatic_ipa_still_incomplete=True,
 previous_goal_turn_classification='no progress: acceleration advice only;revalidated existing source and saved hardware evidence',
 current_goal_turn_classification='progress: preserve419 driver fault evidence and close checkpoint for package integration',
 full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel419/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='1b181f0dae2257fe98288a6907e4c3ae1fd08c22','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for rel in selected:
 target=mirror/rel;data=export.public_bytes(ROOT,rel);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover typed IQ ACK loss and dequeue quiesced error buffers','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=419,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(host.PRIVATE/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
