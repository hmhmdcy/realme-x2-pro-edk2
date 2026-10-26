from pathlib import Path
import io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
action=sys.argv[1];attempt=sys.argv[2] if len(sys.argv)>2 else 'r1';assert attempt.startswith('r') and attempt[1:].isdigit() and 1<=int(attempt[1:])<=20;root='/var/lib/samurai/k428-ds4-'+attempt
if action=='launch':
 assert json.loads((HERE/('capture-staging-'+attempt+'-validation.json')).read_text())['passed']
 code='''from pathlib import Path
import hashlib,json,os,subprocess
root=Path(ROOT);assert not any((root/n).exists() for n in ['state.json','launch.json','worker.log'])
for n,h in json.loads((root/'manifest.json').read_text()).items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid,root=str(root));f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))
'''
elif action=='observe':
 code='''from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
def live(pid):
 try:
  p=Path('/proc',str(pid));return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except OSError:return False
logs={str(p.relative_to(root)):p.read_text(errors='replace')[-4000:] for p in root.rglob('*.log') if p.stat().st_size<2097152}
print(json.dumps(dict(state=s,worker_live=live(s['pid']),client_live=live(s.get('client_pid',-1)),logs=logs)))
'''
elif action=='collect':
 code='''from pathlib import Path
import io,json,sys,tarfile
root=Path(ROOT);assert json.loads((root/'state.json').read_text())['terminal']
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tar:
 for p in root.rglob('*'):
  if p.is_file() and (p.name in ['state.json','failure.txt','kernel-log-private.txt'] or p.suffix=='.log' or p.name.startswith(('full-','ds4-','undelivered-')) and p.suffix=='.bin'):tar.add(p,arcname=str(p.relative_to(root)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=35);q.check_returncode()
if action=='collect':
 out=P/('capture-collected-'+attempt);out.mkdir(exist_ok=True)
 with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:gz') as tar:
  for member in tar.getmembers():
   dest=out/member.name;assert member.isfile() and dest.resolve().is_relative_to(out.resolve());dest.parent.mkdir(exist_ok=True,parents=True);dest.write_bytes(tar.extractfile(member).read())
 print(json.dumps(dict(collected=True,files=len(list(out.rglob('*'))))))
else:
 (P/('capture-'+action+'-'+attempt+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
 if action=='observe' and d['state'].get('terminal'):(HERE/('capture-runtime-'+attempt+'-validation.json')).write_text(json.dumps({k:v for k,v in d.items() if k!='logs'},indent=2)+'\n')
 if action=='observe':
  s=d['state'];brief={k:s[k] for k in ['phase','terminal','passed','captures','formal_modules_restored','services_restored','taint_after','new_faults','failure','cleanup_failure'] if k in s}
  print(json.dumps(dict(state=brief,worker_live=d['worker_live'],client_live=d['client_live'],capture_logs={k:v[-1400:] for k,v in d['logs'].items() if k.endswith('/capture.log')}),indent=2))
 else:print(json.dumps(d,indent=2))
