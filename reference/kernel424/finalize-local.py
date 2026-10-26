"""Verify changed evidence and publish only authored sources/desensitized records locally."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for n in ['build','exposure-domain','ipa','profile','packet','coarse-gap','hardware','scenes','source']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
tree=storage.candidate()/'src/libcamera-v0.7.2';source=json.loads((HERE/'source-validation.json').read_text())
for row in source['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
build=json.loads((HERE/'build-validation.json').read_text());assert build['source_inputs_unchanged_during_build'] and build['actual_changed_ipa_sources_recompiled'] and build['core_proxy_identical_to_validated423']
manifest=json.loads((P/'manifest-r1-private.json').read_text())
for row in build['runtime_files']:
 assert hashlib.sha256((P/row['name']).read_bytes()).hexdigest()==row['sha256']
 key={'libcamera.so.0.7.2':'lib/','ipa_camss_vfe.so':'ipa/','ipa_camss_vfe.so.sign':'ipa/','camss_ipa_proxy':'proxy/'}[row['name']]+row['name']
 assert manifest['payload_sha256'][key]==row['sha256']
r=json.loads((HERE/'runtime-r1-validation.json').read_text());assert r['terminal'] and r['passed'] and r['formal420_unchanged'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==424 and not d['ipe_full_factory_tone_pipeline_complete'] and not d['ipe_ltm_full_dc_coarse_pass_implemented']
 assert d['framework_version']=='99990.7.2-r31' and d['configuration_version']=='0.1.0-r26'
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','archive/NEXT-SESSION-through423-2026-10-21.md',
 'linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
check=module('check424',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
for rel in selected:
 if rel.suffix=='.md':assert not check.link_errors(ROOT,str(rel)),(rel,check.link_errors(ROOT,str(rel)))
 if rel.suffix=='.py':ast.parse((ROOT/rel).read_text())
 if rel.suffix=='.json':json.loads((ROOT/rel).read_text())
for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/n).stat().st_size<=check.load_manifest(ROOT)['size_limits'][n]
report=dict(stage=424,changed_links_json_python_checked=True,source_and_deployed_candidate_payload_hashes_match=True,
 native_binding_and_old_domain_counterexample_verified=True,actual_ipa_missing_bg_recovery_verified=True,
 native_and_isolated_optical_capture_frames=410,numeric_history_commits=402,actual_main_af_reported_focused_both=True,
 formal_runtime_unchanged=True,coarse_dc_gap_proved_by_current_native_commands=True,
 previous_goal_turn_classification='progress:423 actual IPA numeric caller and same-frame requests;144 physical images with native/isolated main scene evidence',
 current_goal_turn_classification='progress:corrected real LTM lux domain and missing-statistics recovery;410 physical AF/auto-tone images;proved missing DC coarse path',
 full_goal_complete=False,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(report,indent=2)+'\n');selected.append(Path('reference/kernel424/documentation-validation.json'))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150'
git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='cd178e21b2ed13080e46a686aed5e7bccb6e8215','Inspect new mirror HEAD'
unrelated=git('diff','--cached','--binary');paths=[]
for rel in sorted(set(selected)):
 out=mirror/rel;data=export.public_bytes(ROOT,rel);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);assert out.read_bytes()==data
 paths.append(str(Path('Platform/Realme/sm8150')/rel))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: correct LTM lux history and recover incomplete statistics with AF capture proof','--',*paths],check=True)
assert git('diff','--cached','--binary')==unrelated and not git('diff','HEAD','--',*paths)
result=dict(stage=424,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
