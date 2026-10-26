"""Check actual r24 deployment on the preserved276 boot, after native AF tests finish."""
from pathlib import Path
R=Path(__file__).resolve().parent
s=(R.parent/'kernel277/inspect-services.py').read_text().replace('stage=277','stage=278').replace('k277-services','k278-services')
compile(s,'inspect-services.py','exec');(R/'inspect-services.py').write_text(s)
s=(R.parent/'kernel277/final-health.py').read_text().replace('k277-final-health','k278-final-health').replace('k277-package','k278-package').replace('k277-services','k278-services').replace('stage=277','stage=278').replace('current49_payloads_verified','current50_payloads_verified').replace('autofocus_algorithm_not_implemented=True','single_auto_af_implemented=True,continuous_and_manual_distance_not_implemented=True')
anchor="tree=Path('/usr/lib/modules')";assert s.count(anchor)==1;s=s.replace(anchor,'assert checked==50\n'+anchor)
compile(s,'final-health.py','exec');(R/'final-health.py').write_text(s)
s=(R.parent/'kernel277/regress-four-cameras.py').read_text().replace('focus-metadata-r1-validation.json','native-af-r1-validation.json').replace('k277','k278').replace('stage=277','stage=278')
anchor="services=json.loads((R/'services-validation.json').read_text());";assert s.count(anchor)==1;s=s.replace(anchor,"assert json.loads((R/'ae-af-r1-validation.json').read_text())['error'] is None\n"+anchor)
compile(s,'regress-four-cameras.py','exec');(R/'regress-four-cameras.py').write_text(s)
print('Actual50 payload, all776 module, service and four-camera checks prepared')
