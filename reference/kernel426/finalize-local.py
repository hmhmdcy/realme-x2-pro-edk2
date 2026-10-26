"""Check changed evidence and save authored sources with a scoped local commit."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
for n in ['codec','producer-geometry','source','intree-build']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
for name in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 assert json.loads((HERE/(name+'-ds4-extraction-validation.json')).read_text())['passed']
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==426 and d['current_device_revalidated_stage']==424
 assert not d['ipe_full_factory_tone_pipeline_complete'] and not d['vfe175_ds4_pixel_dma_runtime_implemented']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through425-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs426',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=426,changed_links_json_python_checked=True,original_tuning_variants=4,original_roots_parsed=64,original_mode_queries=56,
 actual_maintained_c_native_register_cases=768,native_create_execute_contexts=14,original_precrop_depth_packer_geometry_cases=5,
 actual_camss_candidate_symbol_and_werror_build_verified=True,candidate_not_deployed=True,phone_accessed=False,
 ds4_queue_dma_runtime_not_claimed=True,full_dc_statistics_and_image_chain_not_claimed=True,
 previous_goal_turn_classification='progress:425 maintained PD10 coarse IO and Werror build;actual OEM two-pass scheduling and input relocation proved',
 current_goal_turn_classification='progress:426 recovered four-camera OEM DS4 reserves with original XML/mode/parser checks;native register binding and maintained codec implemented/built;producer crop/depth/packer recovered',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel426/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='b62a3d197277e2e260490a6e1613d1ccddaaa8f9','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover OEM DS4 calibration and native VFE175 register composition','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and not git('diff','HEAD','--',*paths)
result=dict(stage=426,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
