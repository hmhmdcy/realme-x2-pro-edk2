from pathlib import Path
import json,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel422')
binary=P/'numeric-history-model'
q=subprocess.run(['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(HERE/'numeric-history-model.cpp'),'-o',str(binary)],capture_output=True)
(P/'numeric-history-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True);(P/'numeric-history-run.log').write_bytes(q.stdout+q.stderr)
assert not q.returncode and b'scenarios=12 passed=1' in q.stdout,q.stderr.decode()
r=dict(stage=422,scenarios=12,asan_ubsan=True,single_uncommitted_calculation_per_camera=True,
    committed_base_revision_required=True,no_dependency_on_failed_or_overlapping_proposals=True,
    observation_completion_cannot_commit_unrelated_numeric_state=True,stop_and_old_epoch_rejected=True,
    runtime_integration_and_hardware_not_claimed=True,passed=True)
(HERE/'numeric-history-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
