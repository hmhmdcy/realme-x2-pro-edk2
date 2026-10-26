from pathlib import Path
import ast,base64,hashlib,io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];root='/var/lib/samurai/k390-reload-r1'
if action=='launch':
 assert json.loads((HERE/'runtime-r2-validation.json').read_text())['passed']
 prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':390")
 source=prefix+'\n'+(HERE/'reload-worker-body.py').read_text();ast.parse(source);worker=P/'reload-worker.py';worker.write_text(source)
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w:gz') as tar:
  tar.add(worker,arcname='worker.py');tar.add(HERE/'dump-collector.py',arcname='dump-collector.py')
 code=r'''from pathlib import Path
import hashlib,io,json,subprocess,sys,tarfile,os
root=Path(ROOT);assert not root.exists();root.mkdir(mode=0o700)
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers();assert {m.name for m in members}=={'worker.py','dump-collector.py'} and all(m.isfile() for m in members)
for m in members:(root/m.name).write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'worker.py').read_bytes()).hexdigest()==WORKER
(root/'pipeline-fixture').symlink_to('/var/lib/samurai/k387-pipeline-r5/pipeline-fixture')
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid);f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))
'''.replace('WORKER',repr(hashlib.sha256(source.encode()).hexdigest()))
 q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),input=payload.getvalue(),timeout=25);(P/'reload-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
elif action=='observe':
 code=r'''from pathlib import Path
import base64,json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
def live(pid,needle):
 try:
  p=Path('/proc',str(pid));return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and needle.encode() in (p/'cmdline').read_bytes()
 except OSError:return False
files={p.name:base64.b64encode(p.read_bytes()).decode() for p in root.iterdir() if p.is_file() and p.stat().st_size<2097152 and (p.suffix in ['.log','.txt'] or p.name in ['state.json','collector-result.json'])}
print(json.dumps(dict(state=s,worker_live=live(s['pid'],str(root/'worker.py')),client_live=live(s.get('client_pid',-1),str(root)),collector_live=live(s.get('collector_pid',-1),str(root/'dump-collector.py')),files=files)))
'''
 q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=30);(P/'reload-observe-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);out=P/'reload-collected-r1';out.mkdir(exist_ok=True)
 for n,v in d['files'].items():(out/n).write_bytes(base64.b64decode(v))
 s=d['state'];keys=['phase','terminal','passed','failure','cleanup_failure','unload_passed','before_removal','reloaded_ready','reloaded_core_state','post_reload_ipe','post_reload_ipe_status','installed_ife_captures','final_status','final_core_state','services_restored','taint_after','collector_result']
 report=dict(stage=390,worker_live=d['worker_live'],client_live=d['client_live'],collector_live=d['collector_live'],new_fault_count=len(s.get('new_faults',[])),**{k:s[k] for k in keys if k in s})
 if s.get('terminal'):(HERE/'reload-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:raise ValueError(action)
