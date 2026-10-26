"""Reuse guarded upload/poll transport and keep unit-data hashes private."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
for name in ['launch-factory-scene.py','poll-factory-scene.py']:
 s=(HERE/name).read_text().replace('factory-scene','calibration-hold').replace('k299-calibration-hold','k299-eeprom-r1')
 if name.startswith('poll-'):
  s=s.replace("(ROOT/'calibration-hold-capture-validation.json').write_text(json.dumps(report['summary'],indent=2)+'\\n')", "(ROOT/'eeprom-read-validation.json').write_text(json.dumps({k:v for k,v in report['summary'].items() if k!='reads'},indent=2)+'\\n')")
  s=s.replace("print(json.dumps(dict(state=state,matching_worker_live=live,", "child=Path('/proc',str(state.get('child_pid',0)));child_live=False\nif child.exists():\n f=(child/'stat').read_text().rsplit(')',1)[1].split();child_live=f[19]==state.get('child_start_ticks') and f[0]!='Z'\nprint(json.dumps(dict(state=state,matching_worker_live=live,matching_power_owner_live=child_live,")
 p=HERE/name.replace('factory-scene','calibration-hold');assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared one-shot EEPROM read workflows; public summary excludes unit-data hashes.')
