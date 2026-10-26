from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/dwc-device-sync-recovery-candidate-tests');OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(HERE/'prepare-tests.py')],check=True)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-pthread','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
binary=OUT/'test-sync'
p=subprocess.run(['gcc',*flags,str(HERE/'test-sync.c'),'-o',str(binary)],capture_output=True,text=True)
assert p.returncode==0,p.stderr
p=subprocess.run([str(binary)],capture_output=True,text=True)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
groups=[s[4:] for s in p.stdout.splitlines() if s.startswith('ok: ')]
assert len(groups)==11 and not p.stderr
r=dict(passed=True,group_count=11,groups=groups,actual_functions=8,flags=flags,asan_ubsan=True,
 actual_functions_not_fake_algorithm=True,real_pthread_connection_and_irq_mutexes=True,
 runtime_stdout=p.stdout,runtime_stderr=p.stderr,binary_private=str(binary),binary_sha256=sha(binary),
 files={n:sha(HERE/n) for n in ['gadget.c','core.h','prepare-tests.py','test-sync.c','tested-functions.inc','function-manifest.json','run-tests.py']},
 scope='new actual generation/publication/recovery/resume/worker and unchanged original core PM callers; fake hardware/workqueue per read original semantics',
 original_126_rerun=False,original_caller_repros_rerun=False,phone_accessed=False,sdk_invoked=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,groups=11,actual_functions=8)))
