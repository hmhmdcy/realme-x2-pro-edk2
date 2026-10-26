"""Save the built GTM/ACK candidate without claiming a hardware receipt."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage433final',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(kernel),'status','--porcelain'])
for name in ['transport','driver','source','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed'],name
for row in state['source_hashes']:assert hashlib.sha256((kernel/row['path']).read_bytes()).hexdigest()==row['sha256']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==433 and not d['latest_work_phone_accessed'] and d['last_live_hardware_evidence_stage']==431 and not d['ipe_gtm_driver_hardware_verified'] and not d['ipe_full_factory_tone_pipeline_complete'] and not d['in_progress_installed']
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through432-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
s=importlib.util.spec_from_file_location('docs433final',ROOT/'linux-port/scripts/docs-health-check.py');check=importlib.util.module_from_spec(s);s.loader.exec_module(check);export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/name).stat().st_size<=check.load_manifest(ROOT)['size_limits'][name]
r=dict(stage=433,changed_links_json_python_checked=True,current_kernel_commit=state['commit'],kernel_driver_candidate_built_not_installed=True,original_ife_execute_cases=7,actual_driver_host_arm64_stock_lut_cases_each=9,matched_intree_modules=10,w1_werror_diagnostics=0,
 private_oem_payload_coefficients_instructions_and_pixels_not_exported=True,gtm_pix_ack_and_sof_hooks_connected=True,physical_gtm_receipt_and_pixels_verified=False,production_ipa_integrated=False,phone_accessed=False,new_scene_frames=0,last_live_evidence_stage=431,last_live_pd10_auto_frames=48,last_live_numeric_commits=48,
 current_goal_turn_classification='progress:433 native complete IFE GTM transport established; typed GTM upload, serialized PIX ACK and SOF snapshot integrated into maintained kernel; actual driver/IRQ checks and matched modules pass; physical and IPA history integration pending',full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel433/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='cb32e82c0ffd94456b9d092c3eaf76650217f00c','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: add IFE GTM candidate with PIX update and SOF receipts','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged and not git('diff','HEAD','--',*paths)
r=dict(stage=433,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,public_export_used=True,pushed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
