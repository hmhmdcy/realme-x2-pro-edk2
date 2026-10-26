from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
r=Path('/var/lib/samurai');p=r/'k265-compat-6000091'
a=(p/'dmesg-before-private.txt').read_text();b=(p/'dmesg-after-private.txt').read_text();lines=b.splitlines()
old_lines=set(a.splitlines());new=lines[len(a.splitlines()):] if b.startswith(a) else [x for x in lines if x not in old_lines]
q=subprocess.run(['sh','-c','command -v gdb; command -v gdbserver'],capture_output=True)
print(json.dumps(dict(current_boot_verified=Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes(),dmesg_new=new[-25:],debuggers=q.stdout.decode().splitlines(),core_pattern=Path('/proc/sys/kernel/core_pattern').read_text().strip()),indent=2))
'''
try:
 q=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'compat-6000091-kernel-private.json').write_bytes(q.stdout);print(q.stdout.decode())
except Exception as e:print(json.dumps(dict(read_failed=type(e).__name__)));raise SystemExit(1)

