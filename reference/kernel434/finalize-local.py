"""Save physical IFE progress without claiming production IPA completion."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage434final',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);K=m.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());assert subprocess.check_output(['git','-C',str(K),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(K),'status','--porcelain'])
for name in ['hardware','source','reopen','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed'],name
live=json.loads((HERE/'runtime-r2-validation.json').read_text());assert live['state']['terminal'] and live['state']['passed'] and not live['worker_live'] and not live['client_live']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==434 and d['latest_work_phone_accessed'] and d['last_live_hardware_evidence_stage']==434 and d['ipe_gtm_driver_hardware_verified'] and not d['ipe_gtm_model2_production_ipa_integrated'] and not d['ipe_full_factory_tone_pipeline_complete'] and not d['in_progress_installed']
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through433-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
s=importlib.util.spec_from_file_location('docs434final',ROOT/'linux-port/scripts/docs-health-check.py');check=importlib.util.module_from_spec(s);s.loader.exec_module(check);export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/name).stat().st_size<=check.load_manifest(ROOT)['size_limits'][name]
r=dict(stage=434,changed_links_json_python_checked=True,current_kernel_commit=state['commit'],matched_intree_modules=10,w1_werror_diagnostics=0,
 private_oem_tables_coefficients_logs_and_pixels_not_exported=True,physical_ife_gtm_receipts_and_pixels_verified=True,pattern_same_sof_sets=61,scene_same_sof_sets=19,both_gtm_banks_repeated_equal=True,
 stopped_stream_initial_parameter_defer_fixed=True,formal_environment_restored=True,new_faults=0,taint=0,production_ipa_gtm_integrated=False,applied_gtm_version_math_history_integrated=False,new_ipe_jobs=0,last_automatic_dual_pass_stage=431,last_automatic_dual_pass_frames=48,
 current_goal_turn_classification='progress:434 stock GTM actual IFE pixels, both-bank repeatability and ACK/SOF association verified; stale PIX RUP initial-packet reopen fixed in driver; 61 pattern and19 scene sets captured; production IPA GTM and successful-history binding pending',full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel434/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='b2f3b25a20c76f794bd7000434ef6b175bc7e6a4','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: verify stock IFE GTM pixels and fix stream reopen ordering','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged and not git('diff','HEAD','--',*paths)
r=dict(stage=434,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,public_export_used=True,pushed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
