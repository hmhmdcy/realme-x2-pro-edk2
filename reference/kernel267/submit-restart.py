"""Submit one restart2 after observed successful quiescence; do not repeat."""
from pathlib import Path
import json
import host

P=host.PRIVATE;marker=P/'reboot-request-private.json';assert not marker.exists()
assert json.loads((P/'quiesce-poll-private.json').read_text())['state']['exit_code']==0
q=host.ssh('python3 /var/lib/samurai/k267-tools/restart-bootloader.py --inspect',timeout=20)
(P/'restart-inspect-private.json').write_bytes(q.stdout)
assert json.loads(q.stdout)['current_boot_guard_pass']
code=r'''
from pathlib import Path
import json,os,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes()
assert json.loads((r/'k267-quiesce/state-private.json').read_text())['exit_code']==0
p=Path('/run/k267-restart-submitted-private.json');assert not p.exists()
p.write_text(json.dumps(dict(request_count=1,restart2_command='bootloader'))+'\n');os.sync()
with Path('/run/k267-restart-worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(r/'k267-tools/restart-bootloader.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=267,restart_worker_submitted=True,pid=child.pid,request_count=1)))
'''
marker.write_text(json.dumps(dict(stage=267,request_count=1,restart2_command='bootloader'))+'\n')
q=host.ssh('python3 -',input=code.encode(),timeout=15)
(P/'restart-submission-private.json').write_bytes(q.stdout);print(q.stdout.decode())
