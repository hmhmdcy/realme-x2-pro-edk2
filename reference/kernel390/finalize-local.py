"""Check changed documents and commit only this checkpoint in the local mirror."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py')
(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through389-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p]
assert (ROOT/'sessions/INDEX.md').read_text()==index.render(ROOT)
validation=dict(stage=390,changed_document_links_checked=True,changed_python_syntax_checked=True,changed_json_parsed=True,entrypoint_size_limits_kept=True,session_index_current=True,source_and_runtime_evidence_separately_verified=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel390/documentation-validation.json'))
selected=sorted(set(selected));repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='dcc9c88587a00ed5ffe7126fc2c93d3f4384f0dc','Inspect new repository tip before committing'
staged_before=git('diff','--cached','--binary')
paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative)
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 assert target.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: deploy the normal SM8150 ICP platform and verify shared ownership','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before,'Unrelated index changed'
assert not git('diff','HEAD','--',*paths)
commit=git('rev-parse','HEAD').decode().strip()
receipt=dict(stage=390,local_commit=commit,files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
private=Path('/mnt/e/edk2-samurai-out/kernel390/local-mirror-validation-private.json');private.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
