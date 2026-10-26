from pathlib import Path
import json
R=Path(__file__).parent;p=R/'snapshot-gui-validation.json';d=json.loads(p.read_text())
for photo in d['gui_control']['new_jpegs']:photo.pop('path',None)
p.write_text(json.dumps(d,indent=2)+'\n')
