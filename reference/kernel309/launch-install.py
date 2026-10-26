"""Install the tested common module once, retaining its original on-device."""
from pathlib import Path
import io,json,shlex,tarfile
import host
HERE=Path(__file__).resolve().parent
proof=json.loads((HERE/'source-state.json').read_text())
proof['old_sha256']=json.loads((HERE.parents[1]/'linux-port/camera/kernel/source-lock.json').read_text())['deployed_camera_modules']['qcom_camss']['sha256']
build=json.loads((HERE/'kernel-build-validation.json').read_text())
data=io.BytesIO()
with tarfile.open(fileobj=data,mode='w:gz') as tar:
    files={'qcom-camss.ko':Path(build['module']),'worker.py':HERE/'native-install.py',
           'pipeline-fixture':host.PRIVATE.parent/'kernel305/pipeline-fixture305-aarch64-private'}
    for name,path in files.items():
        raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700;tar.addfile(item,io.BytesIO(raw))
    raw=json.dumps(proof).encode();item=tarfile.TarInfo('proof.json');item.size=len(raw);item.mode=0o600;tar.addfile(item,io.BytesIO(raw))
code=r'''
from pathlib import Path
import io,subprocess,sys,tarfile
root=Path('/var/lib/samurai/k309-module-install-r1');root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tar:tar.extractall(root,filter='data')
with (root/'worker.log').open('xb') as output:
    p=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,
        stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
print(p.pid)
'''
q=host.ssh('python3 -c '+shlex.quote(code),input=data.getvalue(),timeout=40)
print('Install worker',q.stdout.decode().strip())
