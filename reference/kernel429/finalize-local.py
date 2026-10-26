"""Preserve recovery and the failed feature acceptance in the local mirror."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
for n in ['source','runtime','owner','one-core-oracle','hardware','incident','intree-build','postboot','camera-recovery','single-core-hardware']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
h=json.loads((HERE/'hardware-validation.json').read_text());i=json.loads((HERE/'incident-validation.json').read_text())
assert h['complete_direct_jobs']==4 and not h['feature_acceptance_passed']
assert i['new_oops_caused_by_added_mmio_diagnostic'] and i['device_recovery_complete']
fixed=json.loads((HERE/'single-core-hardware-validation.json').read_text())
assert fixed['complete_direct_jobs']==4 and not fixed['feature_acceptance_passed'] and fixed['taint_after']==0
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==429 and not d['current_device_recovery_required']
 assert not d['ipe_full_factory_tone_pipeline_complete'] and d['last_successful_automatic_ipe_scene_stage']==424
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through428-2026-10-22.md',
 'archive/NEXT-SESSION-429-before-recovery-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs429',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=429,changed_links_json_python_checked=True,native_two_pass_serializer_and_typed_pd10_owner_connected=True,
 paired_source_v4l2_m2m_candidate_connected=True,host_sanitizers_arm64_and_native_command_comparison_passed=True,
 matched_werror_cohort_and_source_replay_verified=True,real_pd10_replay_direct_jobs=4,automatic_ipa_history_commits=0,
 dc_statistics_and_repeatability_not_passed=True,own_added_diagnostic_caused_oops=True,faulting_diagnostic_removed=True,
 latest_fixed_build_not_yet_hardware_validated=False,device_recovery_complete=True,user_physical_restart_completed=True,
 formal_four_camera_recovery_frames=48,fixed_single_core_direct_jobs=4,fixed_single_core_repeatability_not_passed=True,
 formal_disk_modules_unchanged=True,full_pipeline_not_claimed=True,current_formal_device_health_verified=True,
 previous_goal_turn_classification='progress:428 native Crop fix and 144 paired DS4 frames across four physical cameras',
 current_goal_turn_classification='progress:verified physical restart and formal four-camera48-frame recovery; fixed build3 single-core replay completes4 jobs without faults but DC/repeatability still fail; formal modules/services restored',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel429/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='2b7b6520f047d9bd8184067086668a8298b0ecfe','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: verify reboot recovery and fixed single-core PD10 replay','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged
assert not git('diff','HEAD','--',*paths)
r=dict(stage=429,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,
 public_export_used=True,pushed=False,device_recovery_complete=True,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
