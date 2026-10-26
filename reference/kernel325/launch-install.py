import base64,json,shlex,sys
import host
run=sys.argv[1]
code='''
from pathlib import Path
import base64,io,json,subprocess,sys,tarfile
root=Path(ROOT)
if root.exists():print((root/'state.json').read_text());raise SystemExit(0)
root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(sys.stdin.buffer.read())),mode='r:gz') as tar:tar.extractall(root,filter='data')
with (root/'worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'root':str(root)}))
'''.replace('ROOT',repr('/var/lib/samurai/k325-install-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),input=base64.b64encode((host.PRIVATE/'install.tar.gz').read_bytes()),timeout=45)
print(q.stdout.decode())
