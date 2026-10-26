"""Start joint AE/AWB with the deployed module and no consumer restarts."""
from pathlib import Path
import base64,json,shlex
import host
HERE=Path(__file__).resolve().parent
proof=json.loads((HERE/'source-state.json').read_text())
worker=base64.b64encode((HERE/'native-current.py').read_bytes()).decode()
code=r'''
from pathlib import Path
import base64,subprocess
p=Path('/var/lib/samurai/k309-live-worker.py')
p.write_bytes(base64.b64decode(WORKER))
out=Path('/var/lib/samurai/k309-live-worker.log')
with out.open('xb') as f:
    child=subprocess.Popen(['python3',str(p),'/var/lib/samurai/k309-cameras-r4',NOTE],
                           stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
print(child.pid)
'''
code=code.replace('WORKER',repr(worker)).replace('NOTE',repr(proof['module_note_sha256']))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
print('Current-module worker',q.stdout.decode().strip())
