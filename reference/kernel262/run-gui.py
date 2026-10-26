from pathlib import Path
import json
import host
R=Path(__file__).parent
r=host.ssh('python3 -',input=(R/'native-snapshot-gui.py').read_bytes(),timeout=60,check=False)
(host.PRIVATE/'gui-private.log').write_bytes(r.stdout+r.stderr)
try:d=json.loads(r.stdout)
except ValueError:raise RuntimeError('Inspect private GUI worker output') from None
(R/'gui-startup-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
