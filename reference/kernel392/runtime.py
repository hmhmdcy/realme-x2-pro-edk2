from pathlib import Path
import base64,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];attempt=sys.argv[2] if len(sys.argv)>2 else 'r1';assert attempt in ['r1','r2','r3'];root='/var/lib/samurai/k392-runtime-'+attempt
if action=='launch':
 assert json.loads((HERE/('staging-validation.json' if attempt=='r1' else 'staging-'+attempt+'-validation.json')).read_text())['passed']
 code=r'''from pathlib import Path
import hashlib,json,subprocess
root=Path(ROOT);assert not any((root/n).exists() for n in ['launch.json','state.json','worker.log'])
meta=json.loads((root/'manifest.json').read_text())
for n,h in meta['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
d=dict(pid=child.pid);(root/'launch.json').write_text(json.dumps(d));print(json.dumps(d))
'''
elif action=='observe':
 code=r'''from pathlib import Path
import base64,json
root=Path(ROOT);s=json.loads((root/'state.json').read_text())
def live(key,needle):
 p=Path('/proc',str(s.get(key,-1)))
 try:return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and str(root/needle).encode() in (p/'cmdline').read_bytes()
 except OSError:return False
files={p.name:base64.b64encode(p.read_bytes()).decode() for p in root.iterdir() if p.is_file() and p.stat().st_size<2097152 and (p.suffix in ['.log','.txt','.jsonl'] or p.name in ['state.json','collector-result.json'])}
print(json.dumps(dict(state=s,worker_live=live('pid','worker.py'),client_live=live('client_pid','cancel-client'),collector_live=live('collector_pid','dump-collector.py'),files=files)))
'''
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=30);(P/('runtime-'+action+'-'+attempt+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if action=='observe':
 out=P/('runtime-collected-'+attempt);out.mkdir(exist_ok=True)
 for n,v in d.pop('files').items():(out/n).write_bytes(base64.b64decode(v))
 s=d['state'];s['new_fault_count']=len(s.pop('new_faults',[]))
 if s.get('terminal'):(HERE/('runtime-'+attempt+'-validation.json')).write_text(json.dumps(dict(stage=392,**d),indent=2)+'\n')
print(json.dumps(d,indent=2))
