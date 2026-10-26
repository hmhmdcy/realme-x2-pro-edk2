from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel369'
assert json.loads((HERE/'current-health-validation.json').read_text())['healthy']
for name in ['camera-check.py','camera-check-body.py','final-state.py']:
 s=(OLD/name).read_text().replace('k369','k371').replace('stage=369','stage=371').replace("'stage':369","'stage':371")
 if name=='final-state.py':s=s.replace("ssh='strict_original_key_wifi'","ssh='strict_original_key_usb'")
 compile(s,name,'exec');(HERE/name).write_text(s)
print('Prepared relevant post-failure camera recovery checks; no extra reboot requested.')
