"""Publish the offline candidate and retain the independent395 deployment."""
from pathlib import Path
import ast,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['current-state-validation.json','colour-validation.json','colour-arm64-validation.json','enable-abi-validation.json','routing-validation.json','intree-build-validation.json']:assert json.loads((HERE/n).read_text())['passed']
assert not json.loads((HERE/'source-state.json').read_text())['installed']

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through395-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],p
assert (ROOT/'sessions/INDEX.md').read_text()==index.render(ROOT)
validation=dict(stage=396,changed_document_links_checked=True,changed_python_syntax_checked=True,changed_json_parsed=True,entrypoint_size_limits_kept=True,session_index_current=True,source_and_actual_codec_models_and_arm64_build_verified=True,initial_oracle_and_dispatch_fixture_failures_preserved=True,undeployed396_candidate_and_installed395_separate=True,hardware_cc_pixel_and_full_iq_not_claimed=True,full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel396/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='52eb190535a5fe8cc90cd1a5b5a78b22f286208f','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover IPE CCM encoding and verify post-LTM firmware routing','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=396,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
Path('/mnt/e/edk2-samurai-out/kernel396/local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
