from pathlib import Path
import json
import os
import re
import subprocess
base=Path('/var/lib/samurai/k143-rollback-quiesce')
assert os.uname().version.startswith('#143 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==base.joinpath('boot-id-private.txt').read_bytes()
after=subprocess.check_output(['dmesg'],text=True);before=base.joinpath('dmesg-before.txt').read_text()
assert after.startswith(before)
base.joinpath('dmesg-incomplete-private.txt').write_text(after)
delta=after[len(before):]
print(json.dumps(dict(current_kernel=143,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    remoteprocs=[Path('/sys/class/remoteproc/remoteproc'+str(i)+'/state').read_text().strip() for i in range(3)],
    counts={key:delta.count(value) for key,value in [('warnings','WARNING:'),('gpu','gpu fault:'),('dpu','frame done timeout'),('dsi','dsi_err_worker'),('dma','unable to prepare channel'),('bug','BUG:'),('oops','Oops:'),('panic','Kernel panic')]},
    module_ok=base.joinpath('new-module-check.txt').read_text().count(': OK'),archive_present=Path('/tmp/k143-rollback-quiesce-private.tar').exists()),indent=2))
for line in delta.splitlines():
    if re.search(r'NGD |qmi|QMI|unable to prepare channel|id=1 which|WARNING:|ida_free\+|slim_unregister_controller\+',line):
        line=re.sub(r'CPU#\d+:.*$', '[task private]',line)
        print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b','[address]',line))
