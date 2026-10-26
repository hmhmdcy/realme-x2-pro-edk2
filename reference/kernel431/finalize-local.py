"""Export the verified automatic PD10 checkpoint without OEM payloads or pixels."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
storage.mount.mounted_build()
for n in ['source','session','bank','ipa','hardware','build','intree-build','gtm-location','transition-build']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
d=json.loads((HERE/'runtime-r4-validation.json').read_text());s=d['state'];assert s['terminal'] and s['passed'] and not d['worker_live'] and not d['client_live'] and not s['new_faults'] and s['taint_after']==0
assert s['formal_modules_restored'] and s['services_restored']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==431 and d['latest431_ipa_math_history_commits']==48 and not d['ipe_full_factory_tone_pipeline_complete'] and not d['ipe_gtm_applied_version_math_history_association_verified'] and not d['in_progress_installed']
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through430-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
spec=importlib.util.spec_from_file_location('docs431',ROOT/'linux-port/scripts/docs-health-check.py');check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check);export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':
  t=(ROOT/rel).read_text(encoding='utf-8-sig');ast.parse('if True:\n'+t if rel.name=='auto-worker-body.py' else t)
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=431,changed_links_json_and_python_checked=True,private_oem_data_coefficients_instructions_and_images_not_exported=True,
 original_rt_bank_and_reset_command_policy_verified=True,bytewise_average_sram_dump_not_claimed=True,
 real_same_sof_pd10_production_ipa4_connected=True,native_and_isolated_main_auto_images=48,numeric_successful_commits=48,
 bypass_dc_session_transitions_verified=True,earlier_integration_failures_preserved=True,
 ordinary_gtm_mode_manager_queries_verified=14,gtm_math_register_application_or_history_association_complete=False,
 formal_environment_restored=True,new_faults=0,taint_after=0,installed=False,
 previous_goal_turn_classification='progress:430 two-file DC scheduler fix and deterministic cold/persistent coarse consumption',
 current_goal_turn_classification='progress:431 native bank/reset policy established; production same-SOF PD10 plus IPA4 automatic double-pass48frames/48commits; request-mode and deadline fixes; GTM mode selection14queries, applied association pending',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel431/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='c18a02b647dcee6838719a8557e95a4d65409345','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: connect real PD10 to automatic IPA requests and final history','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged and not git('diff','HEAD','--',*paths)
r=dict(stage=431,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,public_export_used=True,pushed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
