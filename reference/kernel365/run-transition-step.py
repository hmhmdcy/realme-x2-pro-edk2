"""Execute a prepared quiesce or one reboot request, preserving observable state."""
from pathlib import Path
import json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1]
assert json.loads((HERE/'pre-transition-validation.json').read_text())['boot_and_logdump_match_retained_rollback']
if action=='quiesce':
    script=(HERE/'native-quiesce.py').read_bytes()
    code=r'''
from pathlib import Path
import subprocess,sys,json
target=Path('/var/lib/samurai/k365-quiesce-worker.py');assert not target.exists();target.write_bytes(sys.stdin.buffer.read())
with Path('/var/lib/samurai/k365-quiesce-worker.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(target)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps(dict(pid=child.pid)))
'''
    q=host.ssh('python3 -c '+shlex.quote(code),input=script,timeout=20);(P/'quiesce-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
elif action=='observe-quiesce':
    code=r'''
from pathlib import Path
import json
root=Path('/var/lib/samurai/k365-quiesce');state=json.loads((root/'state-private.json').read_text());p=Path('/proc',str(state['pid']),'stat')
live=p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z'
print(json.dumps(dict(state=state,worker_live=live,summary=json.loads((root/'summary.json').read_text()) if (root/'summary.json').exists() else None,failure=(root/'failure-private.txt').read_text() if (root/'failure-private.txt').exists() else None)))
'''
    q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(P/'quiesce-observation-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
    print(json.dumps({k:v for k,v in d.items() if k!='failure'},indent=2))
    if d['state']['terminal']:
        assert d['state']['exit_code']==0 and not d['worker_live'],d['failure']
        (HERE/'quiesce-validation.json').write_text(json.dumps(d['summary'],indent=2)+'\n')
elif action=='reboot':
    assert json.loads((HERE/'quiesce-validation.json').read_text())['taint']==0
    marker=P/'reboot-request-private.json';assert not marker.exists()
    # Inspect runs all current quiesce/EUD checks without altering anything.
    s=(HERE/'restart-bootloader.py').read_text();q=host.ssh('python3 -c '+shlex.quote(s)+' --inspect',timeout=25)
    (P/'restart-inspection-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
    marker.write_text(json.dumps(dict(request_count=1,expected_build=363))+'\n')
    q=host.raw_ssh('python3 -c '+shlex.quote(s),timeout=25,check=False)
    (P/'restart-result-private.log').write_bytes(q.stdout+q.stderr)
    print(json.dumps(dict(restart_requested_once=True,ssh_exit=q.returncode,inspect_fastboot_before_any_retry=True)))
else:raise ValueError(action)
