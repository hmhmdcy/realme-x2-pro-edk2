"""Save scoped authored changes and verified DS4 evidence locally."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
for n in ['native-crop-production','runtime-codec','source','intree-build','hardware','pixel-layout']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
h=json.loads((HERE/'hardware-validation.json').read_text());assert h['total_ds4_frames']==h['total_paired_full_frames']==144 and h['ipe_jobs']==0
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==d['last_successful_scene_stage']==428
 assert d['last_successful_automatic_ipe_scene_stage']==424 and d['vfe175_ds4_pixel_dma_runtime_implemented']
 assert not d['ipe_full_factory_tone_pipeline_complete'] and not d['ipe_ltm_full_dc_coarse_pass_implemented']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through427-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs428',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=428,changed_links_json_python_checked=True,whole_original_full_crop_geometry_producer_executed=True,
 original_image_memory_write_guard_passed=True,chroma_x_geometry_corrected_in_maintained_driver=True,
 host_sanitizers_and_arm64_contract_passed=True,matched_werror_cohort_and_source_replay_verified=True,
 phone_accessed=True,complete_ds4_frames=144,same_sof_full_partners=144,four_physical_cameras_sequentially=True,
 starvation_recovery_and_independent_stop_verified=True,pd10_component_packing_and_column_luma_order_verified=True,
 formal_modules_services_resources_restored=True,ipe_jobs=0,last_successful_scene_stage=428,last_successful_automatic_ipe_scene_stage=424,
 previous_goal_turn_classification='progress:427 actual calibrated DS4 transport connected and partial DMA/overflow localized',
 current_goal_turn_classification='progress:428 native FULL Crop produces correct chroma geometry; maintained fix built and 144 paired DS4 frames validated across four cameras',
 full_dc_statistics_and_automatic_chain_not_claimed=True,full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel428/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='199bf06f00f87170d7988397302b9f89196cf9ab','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');before_unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: fix native DS4 chroma crop and validate four-camera paired output','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and not git('diff','HEAD','--',*paths)
assert git('diff','--binary')==before_unstaged,'Unrelated working-tree changes differ'
result=dict(stage=428,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,
 public_export_used=True,pushed=False,pull_request_created=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
