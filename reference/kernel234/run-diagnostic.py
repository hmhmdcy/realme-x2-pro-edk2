"""Install private tools, launch once, then inspect this worker's receipt."""
from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
P = host.PRIVATE
destination = '/var/lib/samurai/k234-tools'
guard = "test \"$(cat /proc/sys/kernel/random/boot_id)\" = \"$(cat /var/lib/samurai/k233-runtime/boot-id-private.txt)\""
host.ssh(guard + ' && test ! -e ' + destination + ' && mkdir -m700 ' + destination)
for source in [P / 'diagnostic-build-r2/hci_uart.ko', R / 'diagnostic-build-validation.json', R / 'native-diagnostic.py']:
    dest = destination + '/' + source.name
    host.upload(source, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(source.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
code = r'''
from pathlib import Path
import json,os,subprocess,time
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-runtime/boot-id-private.txt').read_bytes()
os.umask(0o077)
marker=root/'k234-tools/worker-started-private.json'
assert not marker.exists()
marker.write_text(json.dumps(dict(requested=True))+'\n')
with (root/'k234-tools/worker-private.log').open('xb') as log:
 supervisor="from pathlib import Path; import json,subprocess; p=subprocess.run(['python3','/var/lib/samurai/k234-tools/native-diagnostic.py']); Path('/var/lib/samurai/k234-tools/exit-private.json').write_text(json.dumps({'exit_code':p.returncode})+'\\n')"
 p=subprocess.Popen(['python3','-c',supervisor],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
marker.write_text(json.dumps(dict(requested=True,pid=p.pid,start_ticks=Path('/proc',str(p.pid),'stat').read_text().split()[21]))+'\n')
print(json.dumps(dict(started_once=True)))
'''
result = host.ssh('python3 -', input=code.encode())
(P / 'diagnostic-launch-host-private.log').write_bytes(result.stdout + result.stderr)
state = json.loads((P / 'current-work-private.json').read_text())
state.update(active_native_worker='k234-tools/worker-started-private.json', state='temporary diagnostic worker started; inspect receipt before any further phone mutation')
(P / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(result.stdout.decode().strip())
