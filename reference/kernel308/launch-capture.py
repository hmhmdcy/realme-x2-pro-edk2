"""Launch one new AWB experiment; existing run directories reject replay."""
from pathlib import Path
import io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent
tele=len(sys.argv)>1 and sys.argv[1]=='tele'
version=sys.argv[2] if len(sys.argv)>2 else ('r2' if tele else 'r1')
single=len(sys.argv)>3 and sys.argv[3]=='single'
if not version.startswith('r') or not version[1:].isdigit():raise ValueError('run version')
build=json.loads((HERE/'build-validation.json').read_text())
contract=json.loads((HERE/'ipa-contract-validation.json').read_text())
if build['exit_code'] or not contract['passed']:raise RuntimeError('Candidate is not ready')
module=Path(json.loads((HERE.parent/'kernel307/kernel-build-validation.json').read_text())['module'])
files={'qcom-camss.ko':module,'runtime.tar.gz':host.PRIVATE/'awb-runtime.tar.gz','worker.py':HERE/'native-capture.py'}
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w:gz') as tar:
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700
        tar.addfile(item,io.BytesIO(raw))
code=r'''
from pathlib import Path
import io,subprocess,sys,tarfile
root=Path(RUN_ROOT)
root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:tar.extractall(root,filter='data')
(root/'bundle').mkdir()
with tarfile.open(root/'runtime.tar.gz','r:gz') as tar:tar.extractall(root/'bundle',filter='data')
with (root/'worker.log').open('xb') as output:
    child=subprocess.Popen(['python3',str(root/'worker.py'),str(root),SENSOR,EPOCH_MODE],
                           stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
print(child.pid)
'''
runroot='/var/lib/samurai/k308-awb-'+version
code=code.replace('RUN_ROOT',repr(runroot)).replace('SENSOR',repr('tele' if tele else 'wide'))
code=code.replace('EPOCH_MODE',repr('single' if single else 'double'))
q=host.ssh('python3 -c '+shlex.quote(code),input=archive.getvalue(),timeout=75)
print('AWB worker PID',q.stdout.decode().strip(),'run',runroot)
