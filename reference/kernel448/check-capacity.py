from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
tree=storage.candidate()/'src/libcamera-v0.7.2';header=tree/'src/libcamera/pipeline/camss-vfe/thread_capacity.h'
assert header.read_bytes()==(HERE/'thread_capacity.h').read_bytes()
q=subprocess.run(['g++','-std=c++20','-Os','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie','-pthread','-I'+str(header.parent),str(HERE/'capacity-contract.cpp'),'-o',str(P/'capacity-host')],capture_output=True)
(P/'capacity-host-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
q=subprocess.run([str(P/'capacity-host')],capture_output=True,timeout=30);(P/'capacity-host-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()[-2500:]
result=json.loads(q.stdout);assert result['passed'] and result['cases']==21
W='/private/camss448-capacity';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
shutil.copyfile(header,work/'thread_capacity.h');shutil.copyfile(HERE/'capacity-contract.cpp',work/'contract.cpp')
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-Os','-g','-Wall','-Wextra','-Werror','-pthread','-I'+W,W+'/contract.cpp','-o',W+'/contract'],capture_output=True)
 (P/'capacity-arm-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-2500:]
 q=subprocess.run(['chroot',str(storage.SDK),W+'/contract'],capture_output=True,timeout=60)
 (P/'capacity-arm-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()[-2500:];assert json.loads(q.stdout)==result
r=dict(stage=448,host_asan_ubsan_and_actual_arm64=True,cases=21,actual_production_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),dynamic_allowed_capacity_no_fixed_cpu_mask=True,shared_thread_refcounts_external_policy_and_error_recovery=True,owner_exit_and_cross_thread_release_checked=True,actual_sched_syscalls_restore_original_allowed_mask=True,sdk_bind_unmounted=True,phone_accessed=False,passed=True)
(HERE/'capacity-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
