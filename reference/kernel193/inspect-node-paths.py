from pathlib import Path
import json
base=Path('/sys/firmware/devicetree/base/soc@0')
print(json.dumps(dict(candidates=[p.name for p in base.iterdir() if 'ad' in p.name or '182' in p.name],regulators=[str(p.relative_to(base)) for p in base.glob('rsc*/regulators*')],pin_dirs=[p.name for p in Path('/sys/kernel/debug/pinctrl').iterdir()])))
