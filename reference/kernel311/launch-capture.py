"""Upload the matching candidate bundle and launch one runtime-control capture."""
from pathlib import Path
import base64,json,shlex,sys
import host
HERE=Path(__file__).resolve().parent
run,models=sys.argv[1:3]
submission=json.dumps({'payload':base64.b64encode((host.PRIVATE/'runtime.tar.gz').read_bytes()).decode(),
                       'worker':base64.b64encode((HERE/'native-capture.py').read_bytes()).decode()}).encode()
code=r'''
from pathlib import Path
import base64,io,json,subprocess,sys,tarfile
data=json.loads(sys.stdin.buffer.read());root=Path(ROOT)
if root.exists():print('Existing run: '+(root/'state.json').read_text());raise SystemExit(0)
runtime=Path('/var/lib/samurai/k311-runtime');runtime.mkdir(mode=0o700,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(data['payload'])),mode='r:gz') as tar:tar.extractall(runtime,filter='data')
worker=runtime/'worker.py';worker.write_bytes(base64.b64decode(data['worker']))
with (runtime/('worker-'+RUN+'.log')).open('xb') as log:
    child=subprocess.Popen(['python3',str(worker),str(root),'joint',MODELS],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'root':str(root)}))
'''
for key,value in {'ROOT':'/var/lib/samurai/k311-joint-'+run,'RUN':run,'MODELS':models}.items():code=code.replace(key,repr(value))
q=host.raw_ssh('python3 -c '+shlex.quote(code),input=submission,timeout=45)
print(q.stdout.decode())
