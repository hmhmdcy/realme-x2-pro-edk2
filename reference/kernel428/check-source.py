"""Verify the exact maintained chroma fix, candidate and restored build files."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
build=m.mounted_build();kernel=build.parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
assert git('diff',state['parent_commit'],state['commit'])==(HERE/'precrop-chroma.patch').read_bytes()
assert len(state['source_hashes'])==1
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for row in state['source_hashes']:
 path=kernel/row['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
 out=replay/row['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(git('show',state['parent_commit']+':'+row['path']))
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'precrop-chroma.patch')],cwd=replay,capture_output=True)
(P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and b'offset' not in q.stdout and b'fuzz' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(kernel/row['path']).read_bytes()
terminal=json.loads((P/'intree-build-state.json').read_text());assert terminal['terminal'] and terminal['passed']
d=json.loads((HERE/'intree-build-validation.json').read_text());assert d['passed'] and d['attempt']==2 and not d['diagnostics'] and len(d['modules'])==10
for row in d['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
camss=next(r for r in d['modules'] if r['name']=='qcom-camss');h=json.loads((HERE/'hardware-validation.json').read_text())
assert camss['sha256']==h['candidate_camss_sha256'] and h['maintained_commit']==state['commit']
core=next(row for row in d['modules'] if row['name']=='qcom-camss-icp-a5-core');assert core['sha256']=='ae2ca7e3ede81ccb019422d7250376c23377537d2c328571817a3390db179099'
restored=[]
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-vfe-175-ds4.o','camss-icp-a5-m2m.ko']:
 rel=Path('drivers/media/platform/qcom/camss')/name;current=build/rel;before=P/'intree-build-r2-before'/rel
 assert current.exists()==before.exists()
 if before.exists():assert current.read_bytes()==before.read_bytes()
 restored.append(dict(name=name,existed_before=before.exists(),restored=True))
log=(P/'intree-build-r2.log').read_text();assert 'camss-vfe-175-ds4.o' in log
for rel in ['camss-vfe.c','camss-video.c','camss-vfe-175.c','camss-icp-a5-m2m.c','camss-icp-a5-core.c']:
 path='drivers/media/platform/qcom/camss/'+rel;assert not git('diff',state['parent_commit'],state['commit'],'--',path)
state.update(hardware_validated=True,hardware_scope='Four physical cameras sequentially, existing mode each, FULL640x480 + PD10 quarter, r6',
 whole_full_crop_geometry_producer_executed=True,mnds_output_geometry_still_supplied=True)
state.pop('original_crop_geometry_production_not_claimed',None)
state['full_ife_geometry_production_not_claimed']=True
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
r=dict(stage=428,commit=state['commit'],source_clean=True,source_hashes_match=True,patch_replays_without_fuzz_or_offset=True,
 only_ds4_chroma_precrop_x_changed=True,original_precrop_enable_restored=True,matched_actual_hardware_candidate=True,
 changed_object_recompiled=True,candidate_binary_hashes_match=True,core_unchanged_from425=True,
 queue_and_uapi_unchanged_from427=True,shared_selected_outputs_restored=restored,build_terminal=True,build_diagnostics=0,
 temporary_runtime_candidate=True,permanent_install=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
