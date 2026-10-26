from pathlib import Path
import base64,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];run=sys.argv[2] if len(sys.argv)>2 else 'r1';assert run in ['r1','r2'];root='/var/lib/samurai/k390-runtime-'+run
if action=='launch':
 code=r'''from pathlib import Path
import base64,hashlib,json,os,subprocess
root=Path(ROOT);assert not any((root/n).exists() for n in ['state.json','launch.json','worker.log'])
manifest=json.loads((root/'manifest.json').read_text());p=root/'dump-collector.py';assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['sha256'][p.name]
p.write_bytes(base64.b64decode(COLLECTOR));manifest['sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest();(root/'manifest.json').write_text(json.dumps(manifest)+'\n')
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid);f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))
'''.replace('COLLECTOR',repr(base64.b64encode((HERE/'dump-collector.py').read_bytes()).decode()))
elif action=='observe':
 code=r'''from pathlib import Path
import base64,json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
def live(pid,needle):
 try:
  p=Path('/proc',str(pid));return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and needle.encode() in (p/'cmdline').read_bytes()
 except OSError:return False
files={}
for p in root.iterdir():
 if p.is_file() and p.stat().st_size<2097152 and (p.suffix in ['.log','.txt'] or p.name in ['state.json','native-client.json','pipeline-client.json','camera-state.json','collector-result.json'] or p.name.startswith('case-') and p.suffix=='.nv12'):
  files[p.name]=base64.b64encode(p.read_bytes()).decode()
print(json.dumps(dict(state=s,worker_live=live(s['pid'],str(root/'worker.py')),client_live=live(s.get('client_pid',-1),str(root)),collector_live=live(s.get('collector_pid',-1),str(root/'dump-collector.py')),files=files)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=35);(P/('runtime-'+run+'-'+action+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if action=='observe':
 out=P/('runtime-collected-'+run);out.mkdir(exist_ok=True)
 for n,v in d['files'].items():(out/n).write_bytes(base64.b64decode(v))
 s=d['state'];keys=['phase','terminal','passed','failure','cleanup_failure','export_lifetime_passed','export_client_exit','native_status','final_status','final_core_state','pipeline_completed','native_completed','services_restored','taint_after','clocks_after','collector_result']
 report=dict(stage=390,run=run,worker_live=d['worker_live'],client_live=d['client_live'],collector_live=d['collector_live'],**{k:s[k] for k in keys if k in s})
 report['new_fault_count']=len(s.get('new_faults',[]))
 if s.get('terminal'):
  for p in [HERE/'runtime-validation.json',HERE/('runtime-'+run+'-validation.json')]:p.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:print(q.stdout.decode())
