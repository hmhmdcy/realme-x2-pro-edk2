"""Commit typed CC ownership/pixel evidence without promoting the candidate deployment."""
from pathlib import Path
import ast,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['current-state-validation.json','transfer-validation.json','parcel-validation.json','firmware-parcel-validation.json','pixels-validation.json','intree-build-validation.json','test-intree-build-validation.json']:assert json.loads((HERE/n).read_text())['passed']
assert json.loads((HERE/'runtime-validation.json').read_text())['state']['passed']
assert not json.loads((HERE/'source-state.json').read_text())['installed']
assert not json.loads((HERE/'pixels-validation.json').read_text())['factory_rgb_matrices_ready_for_default']

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through396-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],p
assert (ROOT/'sessions/INDEX.md').read_text()==index.render(ROOT)
validation=dict(stage=397,changed_document_links_checked=True,changed_python_syntax_checked=True,changed_json_parsed=True,entrypoint_size_limits_kept=True,session_index_current=True,actual_cc_parcel_and_ownership_models_verified=True,hardware_fixed_diagonal_pixel_effect_separate_from_full_rgb_calibration=True,first_two_build_failures_preserved=True,temporary397_candidate_and_restored395_runtime_separate=True,all_native_and_normal_counter_epochs_separate=True,full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel397/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='ae126f775bddb88dc8abdf1e7fd43607c686426d','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: own per-frame IPE colour programs and verify hardware pixel effects','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=397,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
Path('/mnt/e/edk2-samurai-out/kernel397/local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
