"""Validate changed checkpoint files and commit only their public mirror paths."""
from pathlib import Path
import ast,importlib.util,json,shutil,subprocess
import storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
assert json.loads((HERE/'current-state-validation.json').read_text())['passed']
candidate=storage.candidate()
shutil.copyfile(HERE/'recipes/libcamera/source-lock.json',candidate/'source-lock.json')
shutil.copyfile(HERE/'recipes/samurai-camera-config/source-lock.json',candidate.parent/'samurai-camera-config391-r30/source-lock.json')
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py')
(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through390-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
selected += [Path('linux-port/packages/libcamera')/p for p in ['APKBUILD','source-lock.json','0040-camss-ipe-pipeline.patch','README.md']]
selected += [Path('linux-port/packages/samurai-camera-config')/p for p in ['APKBUILD','source-lock.json','README.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],p
assert (ROOT/'sessions/INDEX.md').read_text()==index.render(ROOT)
validation=dict(stage=391,changed_document_links_checked=True,changed_python_syntax_checked=True,changed_json_parsed=True,entrypoint_size_limits_kept=True,session_index_current=True,kernel_evidence_reused_from390=True,new_signed_userspace_hardware_verified=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel391/documentation-validation.json'))
selected=sorted(set(selected));repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='cd95639fd528138fb92353370ad76b399dd9386c','Inspect new repository tip before committing'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: install signed IPE pipeline packages and verify default consumers','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before,'Unrelated index changed'
assert not git('diff','HEAD','--',*paths)
receipt=dict(stage=391,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
Path('/mnt/e/edk2-samurai-out/kernel391/local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
