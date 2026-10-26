"""Check changed evidence and save a scoped local public mirror commit."""
from pathlib import Path
import ast,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel405')
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
for name in ['parcel','transfer','firmware-parcel','source-model','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
parcel=json.loads((HERE/'parcel-validation.json').read_text());transfer=json.loads((HERE/'transfer-validation.json').read_text());firmware=json.loads((HERE/'firmware-parcel-validation.json').read_text())
assert all(r['cases']==128 and r['different_bytes']==0 and r['invalid_unchanged_destination']==110 for r in parcel['architectures'])
assert transfer['cases']==145 and len(firmware['cases'])==59 and all(not r['different_cdm_bytes'] and r['job_equal'] for r in firmware['cases'])
assert not json.loads((HERE/'intree-build-validation.json').read_text())['diagnostics']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text());assert not state['installed'] and not state['phone_accessed']
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
for relative in state['changed']:assert (source/relative).read_bytes()==(P/(Path(relative).name+'.proposed')).read_bytes()
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through404-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
 if p.suffix=='.md':assert not check.link_errors(ROOT,str(p)),(p,check.link_errors(ROOT,str(p)))
 if p.suffix=='.py':ast.parse((ROOT/p).read_text())
 if p.suffix=='.json':json.loads((ROOT/p).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for relative in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 d=json.loads((ROOT/relative).read_text());assert d['latest_work_stage']==405 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==402 and not d['latest_stage_phone_accessed'] and not d['ipe_ltm_runtime_submission_enabled'] and d['ipe_ltm_internal_submission_api_added'] and not d['ipe_ltm_hardware_verified']
validation=dict(stage=405,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,source_clean_and_matches_tested_proposal=True,typed_ltm_iq_lut_same_request_ownership=True,internal_api_implemented_but_not_installed_or_hardware_verified=True,parcel128_ownership145_firmware59=True,old_codec_bodies_and_geometry_unchanged=True,fixture_setup_and_guard_corrections_reported=True,last_device402_not_claimed_as405=True,private_original_sources_tables_commands_images_not_exported=True,previous_goal_turn_classification='progress:404 native geometry implemented and built',current_goal_turn_classification='progress:405 typed quantized request implementation and ownership,firmware and build verification',full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel405/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *a:subprocess.check_output(['git','-C',str(repo),*a]);assert git('rev-parse','HEAD').decode().strip()=='bc1d22e4948941359cd95c18b092f8703543e535','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
 target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: retain typed LTM IQ and LUTs in combined IPE requests','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=405,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
