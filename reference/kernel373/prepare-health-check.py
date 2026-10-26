from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel371'
assert json.loads((HERE/'current-health-validation.json').read_text())['healthy']
for name in ['camera-check.py','camera-check-body.py','final-state.py']:
 s=(OLD/name).read_text().replace('k371','k373').replace('stage=371','stage=373').replace("'stage':371","'stage':373")
 compile(s,name,'exec');(HERE/name).write_text(s)
print('Prepared post-failure baseline recovery verification on adopted373 boot.')
