"""Save authored changes and desensitized evidence in a scoped local commit."""
from pathlib import Path
import ast,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
for n in ['io','multipass','source','intree-build']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==425 and d['current_device_revalidated_stage']==424
 assert not d['ipe_full_factory_tone_pipeline_complete'] and not d['ipe_ltm_full_dc_coarse_pass_implemented']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through424-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('docs425',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text(encoding='utf-8-sig'))
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=425,changed_links_json_python_checked=True,actual_maintained_c_io_native_layout_verified=True,
 host_sanitizers_and_arm64_execution_verified=True,actual_core_candidate_werror_build_verified=True,
 full_native_dc_switch_changes_passes_and_commands_verified=True,pd10_iova_relocation_verified=True,
 pd10_pixel_production_and_dc_statistics_not_claimed=True,phone_accessed=False,installed=False,
 previous_goal_turn_classification='progress:424 corrected actual LTM lux domain and missing-statistics recovery;410 real AF/auto-tone images;proved single-pass DC gap',
 current_goal_turn_classification='progress:425 authored maintained PD10 IO/layout,64 native cross-architecture cases and Werror build;actual complete OEM two-pass prepare and IOVA relocation confirmed',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel425/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a])
assert git('rev-parse','HEAD').decode().strip()=='14512f442f6800010f371c627f0cc2825e4b18b2','Inspect changed mirror HEAD'
unrelated=git('diff','--cached','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: recover native PD10 coarse IO and verify actual DC multipass preparation','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and not git('diff','HEAD','--',*paths)
result=dict(stage=425,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
