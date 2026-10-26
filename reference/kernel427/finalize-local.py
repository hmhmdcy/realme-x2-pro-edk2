"""Save scoped authored changes and truthful experiment evidence locally."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
for n in ['queue','runtime-codec','source','intree-build','hardware-investigation']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
h=json.loads((HERE/'hardware-investigation-validation.json').read_text());assert not h['complete_ds4_dma_verified'] and h['hardware_error_status1_seen']=='0x1800'
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==427 and d['current_device_revalidated_stage']==427 and d['last_successful_scene_stage']==424
 assert not d['ipe_full_factory_tone_pipeline_complete'] and not d['vfe175_ds4_pixel_dma_runtime_implemented']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through426-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs427',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=427,changed_links_json_python_checked=True,actual_maintained_driver_and_uapi_connected=True,
 original_node_enable_aggregation_executed=True,host_sanitizers_and_arm64_contracts_passed=True,
 matched_werror_cohort_and_source_replay_verified=True,phone_accessed=True,ds4_feature_experiment_passed=False,
 complete_ds4_frames=0,partial_dma_and_original_camif_overflow_error_evidence_preserved=True,
 formal_modules_services_resources_restored=True,ipe_counters_reset_by_reload_not_job_failure=True,
 last_successful_scene_stage=424,full_dc_statistics_and_automatic_chain_not_claimed=True,
 previous_goal_turn_classification='progress:426 original four-camera DS4 parsing/register binding and maintained codec built; DMA absent',
 current_goal_turn_classification='progress:427 actual DS4 format/queue/WM candidate connected and built; native node enable gap recovered; hardware partial DMA/overflow localized with FULL control and restoration',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel427/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='f7f4f1e812d0c248bba904820aa8f16380b6e2f9','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');before_unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: connect calibrated DS4 capture and document hardware overflow investigation','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and not git('diff','HEAD','--',*paths)
assert git('diff','--binary')==before_unstaged,'Unrelated working-tree changes differ'
result=dict(stage=427,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,
 public_export_used=True,pushed=False,pull_request_created=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
