from pathlib import Path
import hashlib,json,os,pwd,shutil,subprocess,tempfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
contract=json.loads((HERE/'capacity-validation.json').read_text());assert contract['passed']
assert hashlib.sha256((HERE/'thread_capacity.h').read_bytes()).hexdigest()==contract['actual_production_header_sha256']
user=pwd.getpwnam('nobody');assert user.pw_uid!=0
with tempfile.TemporaryDirectory(prefix='camss-capacity-',dir='/tmp') as folder:
 root=Path(folder);root.chmod(0o711);binary=root/'contract';shutil.copyfile(P/'capacity-host',binary);binary.chmod(0o755)
 code='import json,os,subprocess;assert os.getuid()=='+str(user.pw_uid)+';caps=int(next(l.split()[1] for l in open("/proc/self/status") if l.startswith("CapEff:")),16);assert caps==0;print(json.dumps(dict(uid=os.getuid(),effective_capabilities=caps)),flush=True);subprocess.run(['+repr(str(binary))+'],check=True)'
 q=subprocess.run(['runuser','-u','nobody','--','python3','-c',code],capture_output=True,timeout=30)
(P/'capacity-unprivileged-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()[-2500:]
rows=[json.loads(line) for line in q.stdout.splitlines()];assert rows[0]['uid']==user.pw_uid and rows[0]['effective_capabilities']==0 and rows[1]['passed'] and rows[1]['cases']==21 and rows[1]['actual_allowed_mask_restored']
r=dict(stage=448,host_effective_uid=user.pw_uid,effective_capabilities=0,existing_host_sanitized_binary_sha256=hashlib.sha256((P/'capacity-host').read_bytes()).hexdigest(),actual_own_thread_sched_affinity_set_and_restore_without_root=True,phone_accessed=False,passed=True)
(HERE/'unprivileged-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
