from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json
p=Path('/var/lib/samurai/k265-compat-6000091')
a=(p/'dmesg-before-private.txt').read_text();b=(p/'dmesg-after-private.txt').read_text()
lines=b.splitlines();old_lines=set(a.splitlines());new=lines[len(a.splitlines()):] if b.startswith(a) else [x for x in lines if x not in old_lines]
print(json.dumps(dict(dmesg_new=new[-30:],kernel_core_pattern=Path('/proc/sys/kernel/core_pattern').read_text().strip()),indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'compat-6000091-kernel-private.json').write_bytes(q.stdout);print(q.stdout.decode())

