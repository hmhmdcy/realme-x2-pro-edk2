"""Launch a new delay/joint run, or inspect its existing state before any retry."""
from pathlib import Path
import base64,io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent
kind,run,models=sys.argv[1:4]
if kind not in ['delay','joint']:raise ValueError(kind)
worker=base64.b64encode((HERE/'native-capture.py').read_bytes()).decode()
if kind=='delay':payload=(host.PRIVATE/'measurement.tar.gz').read_bytes()
else:
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as tar:
        raw=(host.PRIVATE/'camera-smoke').read_bytes();item=tarfile.TarInfo('bin/camera-smoke');item.size=len(raw);item.mode=0o700
        tar.addfile(item,io.BytesIO(raw))
        for model in models.split(','):
            raw=(HERE/(model+'.yaml')).read_bytes();item=tarfile.TarInfo('profile/'+model+'.yaml');item.size=len(raw);item.mode=0o600
            tar.addfile(item,io.BytesIO(raw))
    payload=out.getvalue()
code=r'''
from pathlib import Path
import base64,io,json,subprocess,sys,tarfile
submission=json.loads(sys.stdin.buffer.read())
root=Path(ROOT)
if root.exists():
    print('Existing run: '+(root/'state.json').read_text());raise SystemExit(0)
runtime=Path('/var/lib/samurai/k310-runtime');runtime.mkdir(mode=0o700,exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(submission['payload'])),mode='r:gz') as tar:tar.extractall(runtime,filter='data')
worker=runtime/'worker.py';worker.write_bytes(base64.b64decode(submission['worker']))
with (runtime/(KIND+'-'+RUN+'-worker.log')).open('xb') as log:
    child=subprocess.Popen(['python3',str(worker),str(root),KIND,MODELS],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'root':str(root)}))
'''
for key,value in {'ROOT':'/var/lib/samurai/k310-'+kind+'-'+run,
                  'KIND':kind,'RUN':run,'MODELS':models}.items():code=code.replace(key,repr(value))
submission=json.dumps({'payload':base64.b64encode(payload).decode(),'worker':worker}).encode()
q=host.ssh('python3 -c '+shlex.quote(code),input=submission,timeout=30)
print(q.stdout.decode())
