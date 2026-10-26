from pathlib import Path
import json
import host
R=Path(__file__).parent
r=host.ssh('python3 -',input=(R/'native-snapshot-gui.py').read_bytes(),timeout=120,check=False);(host.PRIVATE/'snapshot-gui-private.log').write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout)
for photo in (d.get('gui_control') or {}).get('new_jpegs',[]):photo.pop('path',None)
(R/'snapshot-gui-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
