from pathlib import Path
HERE=Path(__file__).resolve().parent
(HERE/'current-health.py').write_text((HERE.parent/'kernel377/current-health.py').read_text().replace('stage=377','stage=379'))
for name in ['camera-check.py','camera-check-body.py']:
 s=(HERE.parent/'kernel375'/name).read_text().replace('stage=375','stage=379').replace("'stage':375","'stage':379").replace('k375-camera-check-','k379-camera-check-').replace('k374-recovered','k378-recovered')
 (HERE/name).write_text(s)
print('Prepared fresh four-camera regression for the adopted 378 boot.')
