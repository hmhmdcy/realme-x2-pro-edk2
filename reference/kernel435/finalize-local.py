"""Save verified main automatic tone progress and retain the full camera goal."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';K=T.parents[2]/'source354'
assert subprocess.check_output(['git','-C',str(K),'rev-parse','HEAD'],text=True).strip()=='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3' and not subprocess.check_output(['git','-C',str(K),'status','--porcelain'])
source=json.loads((HERE/'source-state.json').read_text())
for row in source['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
for n in ['hardware','source','replay','ipa','native-gtm','profile-export','history','retention','statistics-domain','dispatch']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
live=json.loads((HERE/'runtime-r3-validation.json').read_text());assert live['state']['terminal'] and live['state']['passed'] and not live['worker_live'] and not live['client_live']
hardware=json.loads((HERE/'hardware-validation.json').read_text());assert hardware['live_images']==48 and hardware['successful_numeric_history_commits']==42 and hardware['explicit_bootstrap_without_numeric_commit']==6 and not hardware['absolute_image_quality_accepted']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==435 and d['ipe_gtm_model2_production_ipa_integrated'] and d['ipe_gtm_applied_version_math_history_association_verified'] and not d['ipe_main_image_quality_accepted'] and not d['ipe_full_factory_tone_pipeline_complete'] and not d['in_progress_installed']
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through434-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
s=importlib.util.spec_from_file_location('docs435final',ROOT/'linux-port/scripts/docs-health-check.py');check=importlib.util.module_from_spec(s);s.loader.exec_module(check);export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':
  code=(ROOT/rel).read_text(encoding='utf-8-sig')
  ast.parse('try:\n'+code+'\nexcept BaseException:pass\n' if rel.name=='auto-capture-body.py' else code)
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=435,changed_links_json_python_checked=True,userspace_candidate_build=6,private_ipa_version=5,patch_files=15,kernel_unchanged_stage434=True,actual_source_signature_and_patch_replay_verified=True,private_factory_data_and_pixels_not_exported=True,
 ordinary_and_isolated_ipa5_scene_frames_each=24,total_ipe_jobs=48,successful_gtm_tmc_ltm_dual_pass_math_commits=42,explicit_bootstrap_without_math=6,physical_gtm_version_immutable_tmc_same_sof_pd10_and_successful_history_verified=True,formal_environment_restored=True,new_faults=0,taint=0,installed=False,
 image_quality_accepted=False,image_quality_issues=hardware['image_issues'],current_goal_turn_classification='progress:435 production IPA5 stock GTM/TMC/LTM real receipt and immutable TMC bound to same-SOF PD10 and final successful math history;48 live ordinary/isolated images,42 math commits plus6 explicit bootstrap; PD10 eviction/order, control/statistics cycle and threaded state/final receipt ordering fixed; image quality and full multi-camera scope pending',full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel435/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='efd01b4cf0bbbbf966730c53cf381908408c7a27','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: bind applied stock GTM to automatic IPA tone and successful history','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged and not git('diff','HEAD','--',*paths)
r=dict(stage=435,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,public_export_used=True,pushed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
