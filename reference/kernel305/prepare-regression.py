"""Reuse the validated four-camera test and state-restoring fixture on the current boot."""
from pathlib import Path
import base64,hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'geometry-install-validation.json').read_text())['passed']
source=(HERE.parent/'kernel298/native-four-camera-regression.py').read_text()
source=source.replace('k298-four-camera-regression-r1','k305-four-camera-regression-r1').replace('stage=298','stage=305')
source=source.replace('/var/lib/samurai/k298-work/boot-id-private.txt','/var/lib/samurai/k305-geometry-r2/boot-id-private.txt')
source=source.replace("interrupted=index==16;","interrupted=index==16;").replace("['main','main']","['tele','tele']").replace("'interrupting-main'","'interrupting-tele'")
source=source.replace("state='preflight',terminal=False,pid=os.getpid(),runs=[]","state='preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],runs=[]")
source=source.replace("['cam','-c',ids[which],","['/run/samurai305-tools/pipeline-fixture','/dev/media0','/usr/sbin/cam','-c',ids[which],")
# SIGINT goes to the fixture. It forwards the signal and restores before exiting with a
# diagnostic interrupted status; inspect the child's normal exit rather than counting it as a failure.
source=source.replace("p.returncode==0 and not forced","(p.returncode==0 if not interrupted else b'FIXTURE_CHILD status=0 exited=1 exit=0 signalled=0' in stdout) and not forced")
source=source.replace("not forced and (requested","not forced and b'FIXTURE_RESULT result='+ (b'1' if interrupted else b'0') in stdout and (requested")
# Fixtures are bounded at 50 s; all native captures remain bounded by the existing child timeouts.
source=source.replace("report=dict(stage=305,","report=dict(stage=305,per_leg_fixture_restoration=True,")
source=source.replace("save();before=", "save();assert __import__('hashlib').sha256(Path('/usr/lib/modules',os.uname().release,'kernel/drivers/media/i2c/s5k3m5.ko').read_bytes()).hexdigest()=='d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9'\nbefore=")
(HERE/'native-four-camera-regression.py').write_text(source);compile(source,'regression305','exec')
fixture=host.PRIVATE.parent/'kernel300/pipeline-fixture-aarch64-private'
assert hashlib.sha256(fixture.read_bytes()).hexdigest()=='5f5fcbf0300a539327edf699272ffc383a44a3d34bb55ad17ef9ea3ed71b3319'
code=r'''
from pathlib import Path
import hashlib,sys
root=Path('/run/samurai305-tools');assert not root.exists();root.mkdir(mode=0o755)
data=sys.stdin.buffer.read();assert hashlib.sha256(data).hexdigest()=='5f5fcbf0300a539327edf699272ffc383a44a3d34bb55ad17ef9ea3ed71b3319'
p=root/'pipeline-fixture';p.write_bytes(data);p.chmod(0o755);print('FIXTURE_STAGED')
'''
q=host.ssh('python3 -c '+shlex.quote(code),input=fixture.read_bytes(),timeout=20);print(q.stdout.decode())
code=f'''
from pathlib import Path
import base64,json,subprocess
root=Path('/var/lib/samurai/k305-geometry-r3')
assert not Path('/var/lib/samurai/k305-four-camera-regression-r1').exists()
script=root/'four-camera-worker-private.py';assert not script.exists();script.write_bytes(base64.b64decode({base64.b64encode(source.encode()).decode()!r}))
with (root/'four-camera-launch-private.log').open('xb') as log:
 p=subprocess.Popen(['python3',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 print(json.dumps(dict(pid=p.pid,start_ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'regression-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
