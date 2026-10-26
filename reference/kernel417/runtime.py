from pathlib import Path
import base64,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root='/var/lib/samurai/k417-request-r4';action=sys.argv[1]
if action=='launch':
 assert json.loads((HERE/'staging-validation.json').read_text())['passed']
 code=r'''from pathlib import Path
import hashlib,json,os,subprocess
root=Path(ROOT);assert not any((root/n).exists() for n in ['launch.json','state.json','worker.log'])
meta=json.loads((root/'manifest.json').read_text())
for n,h in meta['payload_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
d=dict(pid=child.pid)
with (root/'launch.json').open('x') as f:f.write(json.dumps(d));f.flush();os.fsync(f.fileno())
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
print(json.dumps(d))
'''
elif action=='observe':
 code=r'''from pathlib import Path
import base64,json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
def live(k,names):
 p=Path('/proc',str(s.get(k,-1)))
 try:return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and any(str(root/n).encode() in (p/'cmdline').read_bytes() for n in names)
 except OSError:return False
files={p.name:base64.b64encode(p.read_bytes()).decode() for p in root.iterdir() if p.is_file() and p.stat().st_size<2097152 and (p.suffix in ['.log','.txt','.out','.nv12'] or p.name in ['state.json','collector-result.json'])}
print(json.dumps(dict(state=s,worker_live=live('pid',['worker.py']),client_live=live('client_pid',['request-client','pipeline-fixture']),collector_live=live('collector_pid',['dump-collector.py']),files=files)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=30);(P/('runtime-'+action+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if action=='observe':
 out=P/'runtime-collected-r4';out.mkdir(exist_ok=True)
 for n,v in d.pop('files').items():(out/n).write_bytes(base64.b64decode(v))
 s=d['state'];s['new_unexpected_fault_count']=len(s.pop('new_unexpected_faults',[]))
 if s.get('terminal'):(HERE/'runtime-validation.json').write_text(json.dumps(dict(stage=417,**d),indent=2)+'\n')
if action=='observe':
 s=d['state'];print(json.dumps(dict(phase=s['phase'],terminal=s['terminal'],passed=s.get('passed'),worker_live=d['worker_live'],client_live=d['client_live'],collector_live=d['collector_live'],failure=s.get('failure'),cleanup_failure=s.get('cleanup_failure'),normal395_restored=s.get('normal395_restored'),captures=s.get('captures'),collector=s.get('collector_result'),faults=s.get('new_unexpected_fault_count'),services=s.get('services')),indent=2))
else:print(json.dumps(d,indent=2))
