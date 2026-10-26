from pathlib import Path
import host

code = r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
out=root/'k211-user-libcamera'
logs={p.name:p.read_text(errors='replace') for p in [out/'cam-stdout-private.txt',out/'cam-stderr-private.txt']}
memory={k:v.strip() for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line for k,v in [line.split(':',1)] if k.startswith('Cma') or k in ['MemAvailable','MemFree','MemTotal']}
packages=[]
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
    fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
    if fields.get('P','').startswith('libcamera') or fields.get('P') in ['strace','phosh','wireplumber']:
        packages.append({k:fields[k] for k in ['P','V','A'] if k in fields})
print(json.dumps(dict(logs=logs,memory=memory,packages=packages,strace_available=subprocess.run(['sh','-c','command -v strace'],capture_output=True,text=True).stdout.strip(),taint=Path('/proc/sys/kernel/tainted').read_text().strip())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30)
print(p.stdout.decode())
