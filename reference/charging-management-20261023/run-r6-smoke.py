"""One detached INHIBIT/AUTO check of installed r6; no USB or PM transition."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import shlex

REF = Path(__file__).resolve().parent
OUT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/r6-smoke')

WORKER = '''from pathlib import Path
import fcntl,hashlib,json,os,runpy,time,traceback
os.umask(0o077);out=Path('/root/charging-management-20261023/r6-smoke');out.mkdir(mode=0o700)
def save(name,data):(out/name).write_text(json.dumps(data,indent=2)+'\\n')
fd=os.open('/run/lock/samurai-charging.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
result={'passed':False,'terminal':True,'scope':'r6 installation INHIBIT/AUTO smoke only',
 'physical_full_recharge_accepted':False,'physical_icon_latency_accepted':False,'planned_rtc_pm_accepted':False}
try:
 updater=Path('/root/charging-management-20261023/charging-update-r6-runner.py')
 assert hashlib.sha256(updater.read_bytes()).hexdigest()=='b5cfad278a1d1887e0cb38e47edcb796929b760151e5cb5bb59e775f1e2b2e98'
 u=runpy.run_path(str(updater));io=u['Device']()
 m=io.manager(u['HASHES'][u['SERVICE']]);meta=io.verify(m)
 assert hashlib.sha256(Path(u['MANIFEST']).read_bytes()).hexdigest()==u['NEW']
 io.notes_match(m,meta)
 before=io.observe(m);u['healthy'](before,True);u['unchanged'](before,before)
 assert '[auto]' in (m['live'].PSY/'mp2650-input/charge_behaviour').read_text()
 save('before-private.json',before)
 u['stopped'](io,m,meta)
 time.sleep(2)
 paused=io.observe(m);save('paused-private.json',paused);u['safe_sample'](paused)
 assert paused['sample']['desired_enable']==0 and paused['registers']['08']&0x18==8
 io.manager_command(m,meta,'resume')
 time.sleep(2)
 after=io.observe(m);save('after-private.json',after)
 mode=u['healthy'](after,True);u['unchanged'](before,after)
 assert after['limits']['native_ua']==before['limits']['native_ua']
 assert after['limits']['cv_uv']<=before['limits']['cv_uv']
 result.update(passed=True,accepted_state=mode,restored_auto=True,
  manifest_sha256=u['NEW'],sample=after['sample'],limits=after['limits'],
  inhibited_readback_verified=True,modules_and_camera_services_preserved=True,
  taint=int(after['state']['taint']))
except BaseException:
 result['failure']=traceback.format_exc()
 # An unknown/failed stop or new fault never causes a blind AUTO retry.
 result['automatic_retry_performed']=False
finally:
 save('result.json',result);os.close(fd)
print(json.dumps(result),flush=True)
'''


def main(action, confirmed):
    OUT.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location('window', REF / 'device-window.py')
    window = importlib.util.module_from_spec(spec); spec.loader.exec_module(window)
    if action == 'launch':
        if not confirmed:
            raise SystemExit('Requires explicit current phone-window ownership')
        digest = hashlib.sha256(WORKER.encode()).hexdigest()
        with (OUT / 'launch-request.json').open('x') as stream:
            json.dump({'worker_sha256': digest, 'dispatch_count': 1}, stream)
        (OUT / 'worker.py').write_text(WORKER)
        code = '''from pathlib import Path
import hashlib,json,os,subprocess,sys
os.umask(0o077);base=Path('/root/charging-management-20261023/r6-smoke-runner')
assert not Path('/root/charging-management-20261023/r6-smoke').exists()
assert not any(base.with_suffix(s).exists() for s in ['.py','.pid','.log'])
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()=='944f2d91f66c5642bbcb130c3ef59e022ca6652e599401908f8528a29d34202d'
base.with_suffix('.py').write_bytes(sys.stdin.buffer.read())
with base.with_suffix('.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(base.with_suffix('.py'))],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
base.with_suffix('.pid').write_text(str(child.pid));print(json.dumps({'pid':child.pid,'launched':True}))
'''
        payload = WORKER.encode()
    else:
        payload = None
        code = '''from pathlib import Path
import json
base=Path('/root/charging-management-20261023/r6-smoke-runner');pid=int(base.with_suffix('.pid').read_text())
p=Path('/proc')/str(pid)/'cmdline'
try:
 argv=p.read_bytes().split(bytes([0]));state='alive' if str(base.with_suffix('.py')).encode() in argv else 'pid_reused' if any(argv) else 'unknown'
except FileNotFoundError:state='absent'
except OSError:state='unknown'
directory=Path('/root/charging-management-20261023/r6-smoke')
files={p.name:p.read_text() for p in directory.glob('*.json')} if directory.exists() else {}
print(json.dumps({'process_state':state,'files':files,'log':base.with_suffix('.log').read_text()[-4000:]}))
'''
    q = window.host.ssh('python3 -c ' + shlex.quote(code), input=payload, timeout=30, check=False)
    (OUT / (action + '-stdout-private.json')).write_bytes(q.stdout)
    (OUT / (action + '-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-2000:]); return q.returncode
    data = json.loads(q.stdout)
    if action == 'fetch':
        for name, raw in data['files'].items():
            assert '/' not in name and '\\' not in name
            (OUT / name).write_text(raw)
        result = json.loads(data['files']['result.json']) if 'result.json' in data['files'] else None
        if result is not None:
            (REF / 'r6-smoke-result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'process_state': data['process_state'], 'result': result, 'log': data['log']}, indent=2))
    else:
        print(json.dumps(data))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['launch', 'fetch'])
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args()
    raise SystemExit(main(args.action, args.window_confirmed))
