from pathlib import Path
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel136')
p = json.loads((out/'legacy-vm-operations-private.json').read_text())
matching_other = p['cores'][0]['all_matching_operations']
t = (out/'decoded-legacy-core-private.txt').read_text()
results = []
for line in t.splitlines():
    if not re.search(r'RB_.*(?:BASE|INFO|OPERATION|CCU_CNTL)',line):
        continue
    values = [int(v,16) for v in re.findall(r'0x([0-9a-fA-F]+)',line)]
    match_other = any(m['start']<=v<m['start']+m['size'] for v in values for m in matching_other)
    cleaned = re.sub(r'(?<![A-Za-z_])(?:0x)?[0-9a-fA-F]{4,}(?![A-Za-z_])','<value>',line.strip())
    item = dict(register=cleaned,matches_other_vm_range=match_other)
    if item not in results:
        results.append(item)
(out/'resolve-register-analysis-private.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
