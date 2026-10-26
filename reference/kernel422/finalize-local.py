"""Check only this checkpoint's changed files and create a scoped local commit."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel422')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
for name in ['static','frame','numeric-history','kernel-payload','build','device-read']:
    assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
state=json.loads((HERE/'candidate-source-state.json').read_text());tree=storage.candidate()/'src/libcamera-v0.7.2'
assert state['patch_zero_fuzz_reproduced'] and state['unused_numeric_static_objects_not_linked_into_ipa']
for item in state['source_hashes']:assert hashlib.sha256((tree/item['path']).read_bytes()).hexdigest()==item['sha256']
build=json.loads((HERE/'build-validation.json').read_text());prior=json.loads((HERE.parent/'kernel421/build-validation.json').read_text())
assert build['runtime_files']==prior['runtime_files']
for item in build['runtime_files']:assert hashlib.sha256((P/item['name']).read_bytes()).hexdigest()==item['sha256']
assert json.loads((HERE.parent/'kernel421/signature-validation.json').read_text())['passed']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==422 and d['current_device_revalidated_stage']==421 and d['latest_read_only_device_stage']==422
    assert not d['ipe_media_request_iq_ipa_parameter_generation_integrated'] and not d['ipe_numeric_tmc_ltm_history_integrated']
    assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through421-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs_check422',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
    if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
    if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
    if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:
    assert (ROOT/name).stat().st_size<=check.load_manifest(ROOT)['size_limits'][name]
r=dict(stage=422,changed_document_links_python_syntax_and_json_checked=True,
    numeric_assembly_target_and_host_arm64_verified=True,actual_current_kernel_codec_and_frame_validator_verified=True,
    common_static_library_built_but_no_runtime_ipa_reference=True,runtime_artifacts_identical_to421=True,
    signature_proof_reused_for_identical_ipa=True,automatic_tmc_ltm_not_claimed_complete=True,
    no_new_physical_frames_or_component_install=True,first_oracle_and_provenance_failures_preserved=True,
    previous_goal_turn_classification='progress:421 real observations and receipts;statistics reentry fix verified on hardware',
    current_goal_turn_classification='progress:factory LTM static and complete typed numerical frame assembly;uncommitted numeric-history policy;common library built without runtime caller',
    full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel422/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='f30e0057dbf2250f05c3ccbffdbc67ac6c8e122e','Inspect new mirror HEAD before continuing'
unrelated_index=git('diff','--cached','--binary');paths=[]
for rel in sorted(set(selected)):
    out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    assert out.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: assemble factory LTM numeric frames and versioned history policy','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated_index and not git('diff','HEAD','--',*paths)
result=dict(stage=422,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,
    public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
