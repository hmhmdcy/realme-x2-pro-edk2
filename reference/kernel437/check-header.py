from pathlib import Path
import json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2/src/ipa/camss-vfe'
q=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(T),str(HERE/'awb-status-test.cpp'),'-o',str(P/'awb-status-test')],capture_output=True)
assert not q.returncode,q.stderr.decode();subprocess.run([str(P/'awb-status-test')],check=True)
r=dict(stage=437,actual_header_compiled=True,changed_effective_gains_do_not_reuse_lock=True,older_sof_not_retroactively_locked=True,invalid_and_unconverged_observations_clear_lock=True,reset_clears_lock=True,nonfinite_gains_rejected=True,passed=True)
(HERE/'awb-header-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
