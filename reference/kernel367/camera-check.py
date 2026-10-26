from pathlib import Path
import io,json,re,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;action=sys.argv[1];run_name=sys.argv[2] if len(sys.argv)>2 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run_name);root='/var/lib/samurai/k367-camera-check-'+run_name
if action=='launch':
    assert json.loads((HERE/'services-ready-validation.json').read_text())['ready'],'Normal SSC/desktop must be ready before creating this capture transaction'
    assert json.loads((HERE/'postboot-validation.json').read_text())['new_boot_verified']
    prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':367")
    prefix=prefix.replace(" if q.returncode:raise RuntimeError(label+' failed')", " (root/(label+'-exit.json')).write_text(json.dumps(dict(exit_code=q.returncode)))\n if q.returncode:raise RuntimeError(label+' failed: '+str(q.returncode))")
    worker=prefix+'\n'+(HERE/'camera-check-body.py').read_text();compile(worker,'camera-worker.py','exec')
    payload=io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w:gz') as tar:
        raw=worker.encode();entry=tarfile.TarInfo('worker.py');entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
        tar.add(host.PRIVATE.parent/'kernel363/pipeline-fixture',arcname='pipeline-fixture')
    code=r'''
from pathlib import Path
import io,json,sys,subprocess,tarfile
root=Path(ROOT)
if root.exists():print(json.dumps(dict(existing=True,state=json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else None)));raise SystemExit(0)
root.mkdir(mode=0o700);script=root/'worker.py'
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
 members=tar.getmembers();assert {m.name for m in members}=={'worker.py','pipeline-fixture'} and all(m.isfile() for m in members);tar.extractall(root,filter='data')
with (root/'worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(script),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(pid=child.pid)))
'''.replace('ROOT',repr(root))
    q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=20);(host.PRIVATE/('camera-check-'+run_name+'-launch-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
elif action=='observe':
    code=r'''
from pathlib import Path
import json
root=Path(ROOT);d=json.loads((root/'state.json').read_text());p=Path('/proc',str(d['pid']));live=False
try:live=str(root/'worker.py').encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
except OSError:pass
print(json.dumps(dict(state=d,worker_live=live,failures={p.name:p.read_text() for p in root.glob('*failure*')})))
'''.replace('ROOT',repr(root))
    q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(host.PRIVATE/('camera-check-'+run_name+'-observation-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout);print(json.dumps(d,indent=2))
    if d['state']['terminal']:
        assert not d['worker_live'];report=d['state']['summary'];(HERE/('camera-runtime-'+run_name+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');(HERE/'camera-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
else:raise ValueError(action)
