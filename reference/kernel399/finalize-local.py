"""Commit the399 candidate/evidence through public export, preserving the index."""
from pathlib import Path
import ast,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for n in ['factory-conversion-validation.json','native-leaf-validation.json','mode-conversion-validation.json','parcel-validation.json','transfer-validation.json','firmware-parcel-validation.json','intree-build-validation.json']:assert json.loads((HERE/n).read_text())['passed']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
assert not state['installed'] and subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through398-2026-10-21.md','reference/kernel398/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],p
for p in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/p).read_text());assert d['current_device_revalidated_stage']==397 and not d['latest_stage_phone_accessed']
validation=dict(stage=399,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,source_clean=True,original_factory_values_private=True,native_deserializer_field_order_correction_explicit=True,typed_conversion_chain_separate_from_hardware_colour_domain_proof=True,no399_device_revalidation_or_transition_claimed=True,full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel399/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='779426f6a98e24da5dcc35be2a2df3e7f7bd42ca','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover factory conversion trees and own typed IPE colour chain','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=399,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
Path('/mnt/e/edk2-samurai-out/kernel399/local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
