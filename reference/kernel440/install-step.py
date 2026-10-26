from pathlib import Path
import base64,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];attempt=sys.argv[2] if len(sys.argv)>2 else 'r1';assert attempt in ['r1','r2','r3'];root='/var/lib/samurai/k440-install-'+attempt
if action=='launch':
 assert json.loads((HERE/('install-staging-validation.json' if attempt=='r1' else f'install-staging-{attempt}-validation.json')).read_text())['passed']
 code=r'''from pathlib import Path
import hashlib,json,os,subprocess
root=Path(ROOT);assert not any((root/n).exists() for n in ['state.json','launch.json','worker.log'])
meta=json.loads((root/'stage-manifest-private.json').read_text())
for n,h in meta['files_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
with (root/'worker.log').open('xb') as log:child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid,root=str(root))
with (root/'launch.json').open('x') as f:json.dump(data,f);f.flush();os.fsync(f.fileno())
print(json.dumps(data))
'''
elif action=='observe':
 code=r'''from pathlib import Path
import json,base64
root=Path(ROOT)
def live(pid,needle):
 try:
  p=Path('/proc',str(pid));return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and needle.encode() in (p/'cmdline').read_bytes()
 except OSError:return False
s=json.loads((root/'state.json').read_text());names={'state.json','suite.json','camera-state.json','failure.txt','camera-failure.txt','kernel-log-private.txt','worker.log','suite.log','packages.log','rollback-packages.log','installed-pipewire.log','enumeration.log','pw-enumeration.log','new-wireplumber.log','new-pipewire.log'}
files={p.name:base64.b64encode(p.read_bytes()).decode() for p in root.iterdir() if p.is_file() and p.stat().st_size<4194304 and (p.name in names or p.name.startswith(('gst-','raw-','auto-')) and p.suffix=='.log')}
print(json.dumps(dict(state=s,worker_live=live(s['pid'],str(root/'worker.py')),client_live=live(s.get('client_pid',-1),str(root/'camera-client.py')),files=files)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=45);q.check_returncode();(P/('install-'+action+'-'+attempt+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if action=='observe':
 out=P/('install-collected-'+attempt);out.mkdir(exist_ok=True)
 for n,v in d['files'].items():(out/n).write_bytes(base64.b64decode(v))
 s=d['state'];keys=['phase','terminal','passed','installed','rollback','failure','cleanup_failure','packages','ipe_before','ipe_after_suite','ipe_after','core_after','pipewire','taint_after']
 report=dict(stage=440,worker_live=d['worker_live'],client_live=d['client_live'],service_counts={n:len(v) for n,v in s.get('services',{}).items()},new_fault_count=len(s.get('new_faults',[])),**{k:s[k] for k in keys if k in s})
 if s.get('terminal'):
  (HERE/f'install-{attempt}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
  (HERE/'install-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:print(q.stdout.decode())
