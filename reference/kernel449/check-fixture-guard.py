from pathlib import Path
import json,os,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
binary=P/'pipeline-fixture-long';rows=[]
for setting,expected in [(None,3),('50',3),('350',3),('600',3),('0',2),('601',2),('',2),('invalid',2)]:
 env=dict(os.environ);env.pop('PIPELINE_FIXTURE_TIMEOUT_SECONDS',None)
 if setting is not None:env['PIPELINE_FIXTURE_TIMEOUT_SECONDS']=setting
 q=subprocess.run([str(binary),'/dev/media0','/bin/true'],env=env,capture_output=True,timeout=5)
 assert q.returncode==expected and not q.stdout and not q.stderr
 rows.append(dict(setting=setting,exit_code=q.returncode,stopped_before_media_access=True))
old=(HERE.parent/'kernel363/pipeline-fixture.c').read_text();new=(HERE/'pipeline-fixture-long.c').read_text()
assert old.split('int main(int argc')[0]==new.split('static double monotonic_seconds')[0]
r=dict(stage=449,rows=rows,snapshot_and_restore_functions_byte_identical363=True,old_kernel_release_and_version_guard_unchanged=True,valid_bounds_reach_guard_invalid_bounds_exit_before_guard=True,phone_accessed=False,passed=True)
(HERE/'fixture-guard-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
