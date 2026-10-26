from pathlib import Path
import json
import os
import re
import subprocess

base=Path('/var/lib/samurai/k143-first143-startup')
assert os.uname().version.startswith('#143 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==base.joinpath('boot-id-private.txt').read_bytes()
text=subprocess.check_output(['dmesg'],text=True)
counts={name:text.count(pattern) for name,pattern in [('gpu','gpu fault:'),('dpu','frame done timeout'),('dsi','dsi_err_worker'),('warn','WARNING:'),('dma','unable to prepare channel')]}
print(json.dumps(dict(stage=143,taint=int(Path('/proc/sys/kernel/tainted').read_text()),counts=counts,
    printk_level=int(Path('/proc/sys/kernel/printk').read_text().split()[0]),
    ignore_loglevel=Path('/sys/module/printk/parameters/ignore_loglevel').read_text().strip(),
    display_active='active=1' in Path('/sys/kernel/debug/dri/1/state').read_text()),indent=2))
for line in [line for line in text.splitlines() if re.search(r'dsi_err_worker|nbcon|printing thread|Q6.*ready|SLIM controller Registered',line)][:18]:
    print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b','[address]',line))
