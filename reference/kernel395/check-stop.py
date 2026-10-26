from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'stop-model';work.mkdir(exist_ok=True)
source=(P/'camss-icp-a5-boot.c.proposed').read_text()
def extract(s,name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert m,name;return m.group()
names=['deassert_stopped_reset_locked','quiesce_locked','stop_locked','camss_a5_runtime_suspend']
(work/'body.inc').write_text('\n'.join(extract(source,n) for n in names));(work/'probe.c').write_bytes((HERE/'stop-provider.c').read_bytes())
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);(P/'stop-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-3000:]
for case in range(22):
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True);(work/(str(case)+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(case,q.stderr.decode()[-3000:])
# The old unknown-completion path must violate the held-bridge provider.
old=(P/'camss-icp-a5-boot.c.before').read_text();(work/'body.inc').write_text('\n'.join(extract(old,n) for n in names if n!='deassert_stopped_reset_locked'))
q=subprocess.run(['cc','-std=gnu11','-O1','-Wno-unused-function',str(work/'probe.c'),'-o',str(work/'old-probe')],capture_output=True);assert not q.returncode,q.stderr.decode()[-2000:]
q=subprocess.run([str(work/'old-probe'),'1'],capture_output=True);(work/'old-counterexample.log').write_bytes(q.stdout+q.stderr);assert q.returncode
(work/'body.inc').write_text('\n'.join(extract(source,n) for n in names))
r=dict(stage=395,actual_quiesce_stop_suspend_and_reset_release_functions=True,asan_ubsan=True,cases=22,forced_assert_and_deassert_still_required=True,cpu_readback_required=True,no_csr_or_ipe_or_unmap_while_global_reset_held=True,assert_deassert_readback_and_ipe_failures_retain_backing_and_pm=True,failed_release_retry_before_csr=True,cooperative_path_and_known_sessions_and_idempotent_stop_kept=True,old_held_reset_counterexample_rejected=True,provider_is_not_hardware_proof=True,passed=True)
(HERE/'stop-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
