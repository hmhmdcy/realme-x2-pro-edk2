from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel379'
for name in ['current-health.py','camera-check.py','camera-check-body.py']:
 s=(OLD/name).read_text().replace('stage=379','stage=381').replace("'stage':379","'stage':381").replace('k379-camera-check-','k381-camera-check-')
 (HERE/name).write_text(s)
print('Prepared a fresh four-camera regression after the first IPE pixel transfer; the 378 boot guard is retained.')
