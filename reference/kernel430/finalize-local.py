"""Export only this verified checkpoint, preserving unrelated mirror work."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage430final',HERE.parent/'kernel284/storage.py').mounted_build()
for n in ['source','runtime','io','native-bl','hardware','intree-build','client-build','scene-pair-build','warm-client-build']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
for attempt in ['r1','r2','r3']:
 d=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());s=d['state']
 assert s['terminal'] and s['passed'] and not d['worker_live'] and not d['client_live']
 assert s['formal_modules_restored'] and s['services_restored'] and s['taint_after']==0 and not s['new_faults']
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
h=json.loads((HERE/'hardware-validation.json').read_text());assert h['corrected_direct_jobs']==12 and h['automatic_ipa_or_mathematical_history_commits']==0 and not h['full_factory_auto_pipeline_complete']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==430 and not d['current_device_recovery_required']
 assert d['ipe_ltm_replay_repeatability_verified'] and d['ipe_ltm_dc_consumption_verified'] and not d['ipe_ltm_dc_statistics_verified']
 assert not d['ipe_full_factory_tone_pipeline_complete'] and d['last_successful_automatic_ipe_scene_stage']==424
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through429-recovered-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs430',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=430,changed_links_json_python_checked=True,source_and_cohort_verified=True,
 native_final_pass_distribution_and_whole_program_heap_equivalence_verified=True,
 corrected_direct_jobs=12,control_direct_jobs=4,fresh_same_sof_main_pairs=6,
 fixed_input_repeatability_verified=True,cold_and_persistent_session_outputs_identical=True,
 ltm_coarse_input_consumption_causal_evidence=True,dc_table_byte_export_not_complete=True,
 automatic_ipa_history_commits=0,gtm_applied_version_history_association_complete=False,
 formal_modules_services_resources_restored=True,taint_after=0,new_faults=0,installed=False,
 previous_goal_turn_classification='progress:429 physical restart and four-camera48-frame recovery; fixed single-core replay transport succeeds but repeatability fails',
 current_goal_turn_classification='progress:430 native final scheduler reveals dropped DC stripe; two-file topology/extents fix restores DC and stable coarse consumption in fresh and persistent-session physical replays',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel430/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='e2ef8098ca33fb3924fbaff5afd6f0a6c1e70174','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: restore IPE DC pass scheduling and deterministic coarse consumption','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged
assert not git('diff','HEAD','--',*paths)
r=dict(stage=430,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,public_export_used=True,pushed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
