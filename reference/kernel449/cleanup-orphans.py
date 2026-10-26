"""Only retire orphaned IPA proxies belonging to the ended r1 transaction."""
from pathlib import Path
import json,shlex
import host
code=r'''from pathlib import Path
import json,os,select,signal,time
owned=[];fds=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  args=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
  if not args or not args[0].startswith('/run/user/10000/k449-user-r1-') or Path(args[0]).name!='camss_ipa_proxy':continue
  fd=os.pidfd_open(int(p.name))
  status=(p/'status').read_text();fields=dict(line.split(':',1) for line in status.splitlines() if ':' in line)
  again=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
  assert again==args and int(fields['PPid'])==1 and all(int(x)==10000 for x in fields['Uid'].split())
  owned.append(dict(pid=int(p.name),uid=10000,orphan=True));fds.append(fd)
 except (FileNotFoundError,ProcessLookupError):pass
for fd in fds:signal.pidfd_send_signal(fd,signal.SIGTERM)
remaining=list(fds);deadline=time.monotonic()+5
while remaining and time.monotonic()<deadline:
 ready=select.select(remaining,[],[],max(0,deadline-time.monotonic()))[0];remaining=[fd for fd in remaining if fd not in ready]
for fd in remaining:signal.pidfd_send_signal(fd,signal.SIGKILL)
if remaining:assert len(select.select(remaining,[],[],3)[0])==len(remaining)
for fd in fds:os.close(fd)
print(json.dumps(dict(owned_orphan_proxies=owned,term_signals=len(fds),kill_signals=len(remaining),passed=True)))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();data=json.loads(q.stdout)
(host.PRIVATE/'orphan-cleanup-private.json').write_bytes(q.stdout)
report=dict(stage=449,ended_r1_orphan_ipa_proxies=len(data['owned_orphan_proxies']),only_uid10000_matching_transaction_paths_parent1=True,pidfd_guarded_cleanup=True,term_signals=data['term_signals'],kill_signals=data['kill_signals'],passed=True)
(Path(__file__).resolve().parent/'orphan-cleanup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
