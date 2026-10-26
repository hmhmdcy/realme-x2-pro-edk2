from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';K=T.parents[2]/'source354'
assert subprocess.check_output(['git','-C',str(K),'rev-parse','HEAD'],text=True).strip()=='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3'
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='bae4f75c941658dcc4cb21a152970b2c5f5f49b5'
state=json.loads((HERE.parent/'kernel436/source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
build=json.loads((HERE.parent/'kernel436/build-validation.json').read_text());assert build['passed']
for row in build['runtime_files']:
 path=P.parent/'kernel436'/row['name'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];shutil.copyfile(path,P/row['name'])
build.update(stage=437,reused_unchanged_runtime_stage436=True)
(HERE/'build-validation.json').write_text(json.dumps(build,indent=2)+'\n')
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
for file in ['factory-s5kgw1-private.yaml','bls-corrected-s5kgw1-private.yaml']:shutil.copyfile(P.parent/'kernel436'/file,P/file)
shutil.copyfile(HERE.parent/'kernel436/profile-export-validation.json',HERE/'profile-export-validation.json')
(HERE/'baseline-validation.json').write_text(json.dumps(dict(stage=437,baseline436_sources_match=True,original_bls_corrected_profile_retained=True,previous_turn_classification='progress:436 restored main original BLS and verified229 images/223 math commits plus causal replay;AWB convergence pending',passed=True),indent=2)+'\n')
print('436 matched cohort and corrected original BLS adopted for437 baseline')
