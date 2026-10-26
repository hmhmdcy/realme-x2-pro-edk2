from pathlib import Path
import json,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
text=Path('/var/lib/samurai/k211-quiesce/camera-unload-dmesg-private.txt').read_text();lines=text.splitlines();result=[]
for index,line in enumerate(lines):
    if 'WARNING:' not in line:continue
    block=lines[max(0,index-3):index+90]
    selected=[l for l in block if 'WARNING:' in l or re.search(r'\]\s+[A-Za-z_][A-Za-z_0-9.]*\+0x',l) or 'refcount' in l.lower() or 'unregister' in l.lower() or 'supply' in l.lower() or 'devm_' in l or 'released' in l.lower()]
    result.append(selected)
print(json.dumps(dict(stage=211,warning_count=text.count('WARNING:'),selected_warning_stacks=result,taint=Path('/proc/sys/kernel/tainted').read_text().strip())))
