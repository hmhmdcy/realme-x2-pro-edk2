"""Transfer the focused probe and launch one bounded temporary-module run."""
from pathlib import Path
import io, json, shlex, tarfile, sys
import host
HERE=Path(__file__).resolve().parent
tele=len(sys.argv)>1 and sys.argv[1]=='tele'
build=json.loads((HERE/'kernel-build-validation.json').read_text())
if build['exit_code'] or build['diagnostics']:raise RuntimeError('Build not ready')
files={
 'qcom-camss.ko':Path(build['module']),
 'rgb-probe':host.PRIVATE/('rgb-tele-probe' if tele else 'rgb-probe'),
 'pipeline-fixture':host.PRIVATE.parent/'kernel305/pipeline-fixture305-aarch64-private',
 'worker.py':HERE/'native-probe.py',
}
data=io.BytesIO()
with tarfile.open(fileobj=data,mode='w:gz') as tar:
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700
        tar.addfile(item,io.BytesIO(raw))
code=r'''
from pathlib import Path
import io,subprocess,sys,tarfile
root=Path(RUN_ROOT)
root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:
    tar.extractall(root,filter='data')
with (root/'worker.log').open('xb') as log:
    child=subprocess.Popen(['python3',str(root/'worker.py'),str(root),SENSOR],stdin=subprocess.DEVNULL,
                           stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(child.pid)
'''
code=code.replace('RUN_ROOT',repr('/var/lib/samurai/k307-rgb-r2' if tele else '/var/lib/samurai/k307-rgb-r1')).replace('SENSOR',repr('tele' if tele else 'wide'))
q=host.ssh('python3 -c '+shlex.quote(code),input=data.getvalue(),timeout=30)
print('Probe worker PID:',q.stdout.decode().strip())
