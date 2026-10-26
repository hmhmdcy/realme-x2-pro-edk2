from pathlib import Path
import json
base=Path('/sys/kernel/debug/pinctrl/3100000.pinctrl')
print(json.dumps(dict(group_lines=[s for s in (base/'pinconf-groups').read_text().splitlines() if s.startswith(('12 ','15 ','29 ')) or '(gpio15)' in s],files=[p.name for p in base.iterdir()])))
