"""Check this checkpoint's changed sources/evidence and commit its public export."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for n in ['build','ipa','packet','domains','interpolation','built-caller','roundtrip','hardware','scenes','source']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
tree=storage.candidate()/'src/libcamera-v0.7.2';source=json.loads((HERE/'source-validation.json').read_text())
for row in source['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
build=json.loads((HERE/'build-validation.json').read_text());assert build['attempt']==3 and build['callers_forced_recompiled']
for row in build['runtime_files']:assert hashlib.sha256((P/row['name']).read_bytes()).hexdigest()==row['sha256']
for attempt in ['r2','r3']:
 r=json.loads((HERE/('runtime-'+attempt+'-validation.json')).read_text());assert r['passed'] and r['terminal'] and not any(r[k] for k in ['worker_live','client_live','collector_live']) and r['formal420_unchanged']
 manifest=json.loads((P/('manifest-'+attempt+'-private.json')).read_text())
 for row in build['runtime_files']:
  key={'libcamera.so.0.7.2':'lib/','ipa_camss_vfe.so':'ipa/','ipa_camss_vfe.so.sign':'ipa/','camss_ipa_proxy':'proxy/'}[row['name']]+row['name']
  assert manifest['payload_sha256'][key]==row['sha256']
s=json.loads((HERE/'source-state.json').read_text());s.update(build_pending=False,factory_profiles_not_yet_enabled=False,
 candidate_main_profiles_temporarily_enabled_and_hardware_verified=True,permanent_factory_profile_install=False,
 source_and_compiled_caller_version_verified=True,main_single_exposure_hardware_verified=True,full_factory_pipeline_equivalence=False)
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==423 and d['ipe_candidate_private_ipa_version']==3 and not d['ipe_numeric_tmc_ltm_history_installed']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through422-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('check423',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
r=dict(stage=423,changed_links_json_and_python_checked=True,compiled_source_and_payload_versions_checked=True,
 actual_source_patch_replayed_zero_fuzz=True,real_ipa_contract_and_native_kernel_packets_verified=True,
 native_and_isolated_single_exposure_main_optical_captures=True,image_frames=144,numeric_commits=108,
 factory_tone_numeric_commits=63,failures_preserved=True,formal_install_unchanged=True,
 main_single_exposure_auto_chain_hardware_complete=True,full_factory_pipeline_equivalence=False,
 current_goal_turn_classification='progress:actual IPA3 TMC/LTM caller and numeric receipts;real IFE/IPE colour-gamma roundtrip and main native/isolated optical captures',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(r,indent=2)+'\n');selected.append(Path('reference/kernel423/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='385f4cb0816141367d9bf7587626d11163741e89','Inspect new mirror HEAD'
unrelated=git('diff','--cached','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: run factory TMC LTM through IPA requests and confirmed frame history','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and not git('diff','HEAD','--',*paths)
result=dict(stage=423,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
