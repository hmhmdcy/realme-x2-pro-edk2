from pathlib import Path
import json
r={}
for p in Path('/sys/kernel/debug/pinctrl').glob('*/pinconf-pins'):
 if p.parent.name.endswith('pinctrl'):
  r[p.parent.name]=[l for l in p.read_text().splitlines() if l.startswith(('pin 12 ', 'pin 15 ', 'pin 29 '))]
print(json.dumps(r))
