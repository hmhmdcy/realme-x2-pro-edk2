from pathlib import Path
import hashlib,json,resource,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss437-contract';work=storage.SDK/W.lstrip('/')
assert json.loads((HERE/'awb-module-validation.json').read_text())['passed']
old=P.parent/'kernel436/ipa_camss_vfe.so';shutil.copyfile(old,work/'baseline.so')
def limits():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base',W+'/awb-status',W+'/baseline.so',W+'/factory.yaml','factory',W+'/old.bin'],capture_output=True,timeout=30,preexec_fn=limits)
log=q.stdout+q.stderr;(P/'awb-baseline-counterexample.log').write_bytes(log)
assert q.returncode and b'AWB_CASE sof=5 calculated=0 pending=1 locked=0 expected=1' in log
r=dict(stage=437,original436_ipa_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),same_actual_arm64_harness=True,original_fails_on_pending_gtm_frame_after_convergence=True,current_module_passes_same_case=True,original_failure_retained_privately=True,passed=True)
(HERE/'awb-baseline-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
