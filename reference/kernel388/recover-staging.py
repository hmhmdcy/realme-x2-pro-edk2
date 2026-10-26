"""End only the orphaned stdin receiver; preserve all existing camera state."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code=r'''from pathlib import Path
import json,os,select,signal
root=Path('/var/lib/samurai/k388-pipeline-r1');p=Path('/proc/23617')
assert not root.exists()
assert not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem'])
assert not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists()
result=dict(root_absent=True,worker_never_launched=True,own_receiver_exited=False)
if p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
 fd=os.pidfd_open(23617)
 try:
  cmd=(p/'cmdline').read_bytes();assert cmd.startswith(b'python3\0-c\0') and b"root=Path('/var/lib/samurai/k388-pipeline-r1')" in cmd
  assert b'sys.stdin.buffer.read()' in cmd and b'child=subprocess.Popen' not in cmd
  result['receiver_wchan']=(p/'wchan').read_text().strip()
  signal.pidfd_send_signal(fd,signal.SIGTERM)
  assert select.select([fd],[],[],5)[0]
 finally:os.close(fd)
result['own_receiver_exited']=not p.exists() or (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z'
assert result['own_receiver_exited'] and not root.exists()
print(json.dumps(result))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);(host.PRIVATE/'staging-recovery-private.json').write_bytes(q.stdout);print(q.stdout.decode())
d=json.loads(q.stdout)
report=dict(stage=388,pipeline_staging_run='r1',upload_interrupted=True,root_not_created=True,manifest_not_written=True,worker_never_launched=True,orphaned_stdin_receiver_terminated_after_pidfd_identity_check=True,receiver_exited=d['own_receiver_exited'],no_camera_experiment_started=True,passed=True)
(HERE/'staging-r1-validation.json').write_text(json.dumps(report,indent=2)+'\n')
