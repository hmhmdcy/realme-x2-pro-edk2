from pathlib import Path
import base64,json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent
run,selection=sys.argv[1:3];assert re.fullmatch(r'r[1-9][0-9]*',run)
cases=json.loads((host.PRIVATE/'cases-private.json').read_text());assert selection=='all' or all(s in cases for s in selection.split(','))
code=r'''
from pathlib import Path
import base64,io,json,subprocess,sys,tarfile
root=Path(ROOT)
if root.exists():
 print(json.dumps(dict(existing=True,state=json.loads((root/'state.json').read_text()) if (root/'state.json').exists() else None)));raise SystemExit(0)
root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(sys.stdin.buffer.read())),mode='r:gz') as tar:tar.extractall(root,filter='data')
with (root/'worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(root/'worker.py'),str(root),SELECTION],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(pid=child.pid,root=str(root))))
'''.replace('ROOT',repr('/var/lib/samurai/k362-request-'+run)).replace('SELECTION',repr(selection))
q=host.ssh('python3 -c '+shlex.quote(code),input=base64.b64encode((host.PRIVATE/'probe.tar.gz').read_bytes()),timeout=45)
(host.PRIVATE/('launch-'+run+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
