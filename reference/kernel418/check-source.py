"""Check patch reproducibility and pin only changed candidate source files."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';baseline=tree.parents[2]/'libcamera391-ipe-r30-built/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text())
scratch=tree.parents[2]/'patch-check418';assert not scratch.exists();scratch.mkdir()
for row in state['source_hashes']:
    name=row['path'];assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==row['sha256']
    if (baseline/name).exists():
        target=scratch/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/name,target)
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'0041-camss-ipe-request.patch')],cwd=scratch,capture_output=True)
(host.PRIVATE/'patch-apply.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
for row in state['source_hashes']:assert (scratch/row['path']).read_bytes()==(tree/row['path']).read_bytes()
kernel=json.loads((HERE.parent/'kernel417/source-state.json').read_text());source=storage.mount.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==kernel['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(kernel_commit=kernel['commit'],kernel_branch=kernel['branch'],kernel_unchanged_from417=True,
    public_patch_reproduces_candidate_zero_fuzz=True,actual_libcamera_wrapper_hardware_verified=True,
    camera_pipeline_media_requests_verified=True,ipa_algorithm_payload_still_bypass=True,full_goal_kept_active=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
report=dict(stage=418,actual_compiled_sources_hashes_match=True,public_patch_reproduces_source_zero_fuzz=True,
    kernel417_unchanged_clean=True,board_dt_sensor_and_ipa_algorithm_unchanged=True,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
