from pathlib import Path
import host
code=r'''
from pathlib import Path
import collections,json,re,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
out=root/'k211-user-libcamera-system'
before=(out/'dmesg-before-private.txt').read_text();after=(out/'dmesg-after-private.txt').read_text()
old=before.splitlines();lines=after.splitlines();delta=lines[len(old):] if lines[:len(old)]==old else lines
warnings=collections.Counter(re.sub(r'^\[[^]]+\]\s*','',x) for x in delta if 'WARNING:' in x)
first=next((i for i,x in enumerate(delta) if 'WARNING:' in x),None)
context=[]
if first is not None:
    for line in delta[max(0,first-4):first+90]:
        if any(x in line for x in ['WARNING:',' at ','Call trace:','+0x','---[ end trace','DMA','dma','buffer','vb2_']):context.append(line)
rp={p.name:(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
print(json.dumps(dict(taint=Path('/proc/sys/kernel/tainted').read_text().strip(),warnings=dict(warnings),first_warning_context=context,cam_stderr=(out/'cam-stderr-private.txt').read_text(),cam_stdout=(out/'cam-stdout-private.txt').read_text(),remoteprocs=rp,sensor_status=Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'capture-warning-context-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
