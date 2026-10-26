"""Launch a new bounded multi-camera worker."""
from pathlib import Path
import io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent
models=sys.argv[1] if len(sys.argv)>1 else 's5kgw1,imx471'
kind=sys.argv[2] if len(sys.argv)>2 else 'manual'
version=sys.argv[3] if len(sys.argv)>3 else 'r1'
if not version.startswith('r') or not version[1:].isdigit():raise ValueError('version')
proof=HERE/'kernel-build-validation.json'
if not proof.exists():proof=HERE.parent/'kernel307/kernel-build-validation.json'
build=json.loads(proof.read_text())
if build['exit_code'] or build['diagnostics']:raise RuntimeError('CAMSS build is not ready')
module=Path(build['module'])
verify_raw=len(sys.argv)>4 and sys.argv[4]=='raw'
files={'qcom-camss.ko':module,'runtime.tar.gz':host.PRIVATE/'runtime.tar.gz','worker.py':HERE/'native-capture.py'}
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w:gz') as tar:
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700
        tar.addfile(item,io.BytesIO(raw))
code=r'''
from pathlib import Path
import io,subprocess,sys,tarfile
root=Path(RUN_ROOT);root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:tar.extractall(root,filter='data')
(root/'bundle').mkdir()
with tarfile.open(root/'runtime.tar.gz','r:gz') as tar:tar.extractall(root/'bundle',filter='data')
with (root/'worker.log').open('xb') as output:
    child=subprocess.Popen(['python3',str(root/'worker.py'),str(root),MODELS,KIND,RAW],
        stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
print(child.pid)
'''
runroot='/var/lib/samurai/k309-cameras-'+version
code=code.replace('RUN_ROOT',repr(runroot)).replace('MODELS',repr(models)).replace('KIND',repr(kind))
code=code.replace('RAW',repr('raw' if verify_raw else 'no-raw'))
q=host.ssh('python3 -c '+shlex.quote(code),input=archive.getvalue(),timeout=75)
print('Worker',q.stdout.decode().strip(),runroot)
