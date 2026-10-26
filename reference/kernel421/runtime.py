from pathlib import Path
import base64,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];attempt=sys.argv[2] if len(sys.argv)>2 else 'r1';assert attempt in ['r1','r2'];root='/var/lib/samurai/k421-history-'+attempt
if action=='launch':
 assert json.loads((HERE/('staging-validation.json' if attempt=='r1' else 'staging-r2-validation.json')).read_text())['passed']
 code=r'''from pathlib import Path
import hashlib,json,os,subprocess
root=Path(ROOT);assert not any((root/n).exists() for n in ['state.json','launch.json','worker.log'])
meta=json.loads((root/'stage-manifest-private.json').read_text())
for n,h in meta['files_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid,root=str(root));f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))
'''
elif action=='observe':
 code=r'''from pathlib import Path
import base64,json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
def live(pid,needle):
 try:
  p=Path('/proc',str(pid));return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and needle.encode() in (p/'cmdline').read_bytes()
 except OSError:return False
files={p.name:base64.b64encode(p.read_bytes()).decode() for p in root.iterdir() if p.is_file() and p.stat().st_size<2097152 and (p.suffix in ['.log','.txt','.out'] or p.name in ['state.json','suite.json','camera-state.json','collector-result.json'])}
print(json.dumps(dict(state=s,worker_live=live(s['pid'],str(root/'worker.py')),client_live=live(s.get('client_pid',-1),str(root/'camera-client.py')),collector_live=live(s.get('collector_pid',-1),str(root/'dump-collector.py')),files=files)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=35);(P/('runtime-'+action+'-'+attempt+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if action=='observe':
 out=P/('runtime-collected-'+attempt);out.mkdir(exist_ok=True)
 for n,v in d['files'].items():(out/n).write_bytes(base64.b64decode(v))
 s=d['state'];keys=['phase','terminal','passed','failure','cleanup_failure','before','after_candidate','candidate_suite','formal_front','formal420_unchanged','after','core_after','taint','collector_result']
 report=dict(stage=421,worker_live=d['worker_live'],client_live=d['client_live'],collector_live=d['collector_live'],service_counts={n:len(v) for n,v in s.get('services',{}).items()},new_fault_count=s.get('new_fault_count',0),**{k:s[k] for k in keys if k in s})
 if s.get('terminal'):
  (HERE/('runtime-'+attempt+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
  (HERE/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:print(q.stdout.decode())
