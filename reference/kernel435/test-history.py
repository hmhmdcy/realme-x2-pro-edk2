from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';W=P/'history-test';W.mkdir(exist_ok=True)
for n in ['ife_gtm_history.h','ipe_numeric_history.h']:shutil.copyfile(T/'src/ipa/camss-vfe'/n,W/n)
shutil.copyfile(HERE/'gtm-history-test.cpp',W/'test.cpp')
q=subprocess.run(['g++','-std=c++20','-Wall','-Wextra','-Werror','-O2','-fsanitize=address,undefined','-no-pie','-I'+str(W),'-I'+str(T/'include'),str(W/'test.cpp'),'-o',str(W/'test')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(W/'test')],capture_output=True);assert not q.returncode,q.stderr.decode();assert b'GTM_HISTORY_PASS' in q.stdout
r=dict(stage=435,actual_history_headers=True,host_asan_ubsan=True,submission_does_not_apply=True,causal_source_sof_enforced=True,invalid_unknown_and_wrong_generation_receipts_rejected=True,frame_keeps_immutable_old_version=True,ipe_failure_does_not_roll_back_ife=True,successful_numeric_history_uses_bound_version=True,unsubmitted_cancel_and_reset_checked=True,passed=True)
(HERE/'history-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
