"""Commit scoped402 correction/evidence locally, preserving unrelated work."""
from pathlib import Path
import ast,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for name in ['dmi-correction','downstream','parcel','transfer','firmware-parcel','intree-build','pixels','current-state']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert not json.loads((HERE/'pixels-validation-r1.json').read_text())['passed']
for name in ['runtime-validation.json','runtime-validation-r1.json']:
 r=json.loads((HERE/name).read_text());assert r['state']['passed'] and r['state']['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert not state['installed'] and subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['reference/kernel401/README.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through401-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==402 and d['ipe_gamma_hardware_verified'] and not d['a5_icp_candidate_source_installed']
validation=dict(stage=402,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,source_clean=True,original_type3_fixture_error_and_failed_r1_retained=True,corrected_type1_and_physical_pixel_scope_explicit=True,private_factory_values_and_images_not_exported=True,both_transaction_processes_terminal=True,native_and_normal_counter_epochs_separate=True,formal395_restored=True,full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel402/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='86d532ab1fa925dc5c80852f4f992a0e16406487','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: fix Gamma DMI command type and verify hardware pixels','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=402,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
Path('/mnt/e/edk2-samurai-out/kernel402/local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
