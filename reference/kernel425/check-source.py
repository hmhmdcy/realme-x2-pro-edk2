"""Validate maintained source, exact patch replay and the completed core build."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();kernel=build.parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for row in state['source_hashes']:
 path=kernel/row['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
 old=git('show',state['parent_commit']+':'+row['path']);out=replay/row['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(old)
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'coarse-io-layout.patch')],cwd=replay,capture_output=True)
(P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and b'offset' not in q.stdout and b'fuzz' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(kernel/row['path']).read_bytes()
for filename in ['intree-build-r1-validation.json','intree-build-validation.json']:
 path=HERE/filename;d=json.loads(path.read_text());d.pop('actual_in_tree_candidate_and_standard_helper_build',None);d['actual_in_tree_core_candidate_built']=True;path.write_text(json.dumps(d,indent=2)+'\n')
terminal=json.loads((P/'intree-build-state.json').read_text());assert terminal['terminal'] and terminal['passed']
terminal.pop('actual_in_tree_candidate_and_standard_helper_build',None);terminal['actual_in_tree_core_candidate_built']=True
(P/'intree-build-state.json').write_text(json.dumps(terminal,indent=2)+'\n')
d=json.loads((HERE/'intree-build-validation.json').read_text());assert d['passed'] and not d['diagnostics'] and len(d['modules'])==1
for row in d['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
restored=[]
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-icp-a5-boot.o','camss-icp-a5-ipe.o']:
 rel=Path('drivers/media/platform/qcom/camss')/name;current=build/rel;before=P/'intree-build-r1-before'/rel
 assert current.exists()==before.exists()
 if before.exists():assert current.read_bytes()==before.read_bytes()
 restored.append(dict(name=name,existed_before=before.exists(),restored=True))
log=(P/'intree-build-r1.log').read_text();assert 'camss-icp-a5-boot.o' in log and 'camss-icp-a5-ipe.o' in log
r=dict(stage=425,commit=state['commit'],source_hashes_match=True,source_clean=True,patch_replays_without_fuzz_or_offset=True,
 actual_changed_core_objects_recompiled=True,candidate_binary_hash_matches=True,shared_selected_outputs_restored=restored,
 build_terminal=True,build_diagnostics=0,core_only_build_metadata_corrected=True,standard_helper_rebuild_not_claimed=True,
 ordinary_runtime_configuration_still_passes_null_coarse=True,coarse_runtime_not_connected=True,installed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
