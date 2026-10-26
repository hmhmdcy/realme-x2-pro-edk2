from pathlib import Path
import json
import os
import re
import subprocess

root=Path('/var/lib/samurai/k143-quiesce')
assert os.uname().version.startswith('#140 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==root.joinpath('boot-id-private.txt').read_bytes()
text=subprocess.run(['dmesg'],capture_output=True,text=True,check=True).stdout
root.joinpath('dmesg-incomplete-private.txt').write_text(text)
before=root.joinpath('dmesg-before.txt').read_text()
report=dict(stage=143,current_kernel=140,same_quiesce_boot=True,
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    module_ok=root.joinpath('new-module-check.txt').read_text().count(': OK'),
    module_failed=root.joinpath('new-module-check.txt').read_text().count('FAILED'),
    partition_ok=root.joinpath('partition-check.txt').read_text().count(': OK'),
    remoteprocs=[Path('/sys/class/remoteproc/remoteproc'+str(i)+'/state').read_text().strip() for i in range(3)],
    warning_count_before=before.count('WARNING:'),warning_count_after=text.count('WARNING:'),
    archive_present=Path('/tmp/k143-quiesce-private.tar').exists(),goal_complete=False)
root.joinpath('incomplete-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
lines=text.splitlines()
warnings=[index for index,line in enumerate(lines) if 'WARNING:' in line]
for index in warnings:
    for line in lines[max(0,index-2):index+65]:
        if re.search(r'WARNING:|ida_free|not allocated|Call trace:|^\[.*\]\s+[A-Za-z_][A-Za-z0-9_]*\+',line):
            line=re.sub(r'CPU#\d+:.*$', '[task private]',line)
            print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b','[address]',line))
