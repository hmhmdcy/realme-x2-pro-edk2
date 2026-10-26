"""Export the offline GTM checkpoint, preserving unrelated mirror changes."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage432final',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.mounted_build()
for name in ['factory-gtm','native-parse','native-math','adrc','portable']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed'],name
assert json.loads((HERE/'portable-validation.json').read_text())['native_selector_swap_bank_combinations']==12
assert json.loads((HERE/'source-state.json').read_text())['maintained_kernel_clean']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==432 and not d['latest_work_phone_accessed'] and d['last_live_hardware_evidence_stage']==431 and not d['ipe_gtm_applied_version_math_history_association_verified'] and not d['ipe_full_factory_tone_pipeline_complete'] and not d['in_progress_installed']
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through431-2026-10-22.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
s=importlib.util.spec_from_file_location('docs432final',ROOT/'linux-port/scripts/docs-health-check.py');check=importlib.util.module_from_spec(s);s.loader.exec_module(check);export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/name).stat().st_size<=check.load_manifest(ROOT)['size_limits'][name]
sources=['reference/kernel432/libipa/gtm_tmc11.cpp','reference/kernel432/libipa/gtm_tmc11.h','reference/kernel432/gtm-runner.cpp','reference/kernel412/libipa/tmc11_ltm.cpp','reference/kernel412/libipa/tmc11_ltm.h']
assert (P/'portable-host-actual-private.bin').read_bytes()==(P/'portable-expected-private.bin').read_bytes()==(P/'portable-aarch64-actual-private.bin').read_bytes()
for name in sources:assert (ROOT/name).stat().st_mtime<=(P/'portable-host-actual-private.bin').stat().st_mtime
r=dict(stage=432,changed_links_json_and_python_checked=True,compiled_own_source_hashes=[dict(path=n,sha256=hashlib.sha256((ROOT/n).read_bytes()).hexdigest()) for n in sources],
 original_gtm_roots_decoded_xml_and_native_parsed=45,original_gtm_active_tmc11_calculations=9,host_and_arm64_portable_cases_each=27,native_independent_packing_cases=12,
 final_native_lut_write_coverage_verified=True,early_offline_fixture_failures_superseded=True,private_factory_tables_and_instructions_not_exported=True,phone_accessed=False,new_scene_frames=0,
 last_live_evidence_stage=431,last_live_real_auto_pd10_frames=48,last_live_numeric_commits=48,gtm_register_application_or_history_association_complete=False,production_ipa_integrated=False,installed=False,
 current_goal_turn_classification='progress:432 factory GTM45 roots/XML/native parse; complete stock TMC11 to GTM calculation; portable model2 GTM matches host/ARM64 and native independent packing branches',full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel432/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='99894550bdd30c4c1df3ff28358f40bae292fbad','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');unstaged=git('diff','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover stock GTM and verify portable TMC11 GTM math','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and git('diff','--binary')==unstaged and not git('diff','HEAD','--',*paths)
r=dict(stage=432,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_and_working_changes_preserved=True,public_export_used=True,pushed=False,full_goal_complete=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
