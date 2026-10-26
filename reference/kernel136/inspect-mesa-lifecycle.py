from pathlib import Path
import json
import runpy
import re

r = Path('/mnt/e/RealmeX2Pro edk2')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
root = Path('/home/cy122/pmos-samurai-kernel118/mesa-offline/mesa-26.2.4')
paths = [p for p in (root / 'src/gallium/drivers/freedreno').rglob('*') if p.suffix in ['.cc','.c','.h','.cpp']]
for path in paths:
    text = path.read_text()
    if 'FD_CCU_RESOLVE' in text:
        lines = text.splitlines()
        print(str(path.relative_to(root)))
        for i,line in enumerate(lines):
            if 'FD_CCU_RESOLVE' in line:
                print('\n'.join(lines[max(0,i-12):i+13]))
out = Path('/mnt/e/edk2-samurai-out/kernel136')
p = json.loads((out / 'legacy-correlation-private.json').read_text())
pid = p['same_vm_ops'][0]['pid']
vm_labels = {vm:chr(65+i) for i,vm in enumerate(sorted(set(s['ttbr'] for s in json.loads((out/'legacy-vm-operations-private.json').read_text())['switches'])))}
allp = json.loads((out/'legacy-vm-operations-private.json').read_text())
items = []
for m in allp['switches']:
    items.append(dict(time=m['time'],event='switch',vm=vm_labels[m['ttbr']],probe_pid=m['pid']==pid,seq=m['seq'],old_ctx=m['old_ctx'],new_ctx=m['new_ctx']))
for e in p['events']:
    fields = dict(re.findall(r'(\w+)=(-?\d+)',e['fields']))
    items.append(dict(time=e['time'],event=e['event'],submit_id=int(fields['id']),probe_pid=int(fields['pid'])==pid))
for line in (out/'submission-trace-private.txt').read_text().splitlines():
    m = re.search(r'([0-9.]+): (msm_gpu_suspend|msm_gpu_resume):',line)
    if m:
        items.append(dict(time=float(m[1]),event=m[2]))
items.sort(key=lambda x:x['time'])
print(json.dumps(items,indent=2))
(r / 'reference/kernel136/legacy-submit-timeline.json').write_text(json.dumps(items,indent=2)+'\n')
