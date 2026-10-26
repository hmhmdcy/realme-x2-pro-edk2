"""Enable new-mode 3A only after independent control timing measurement."""
from pathlib import Path
import copy,json,yaml
class PlainYaml(yaml.SafeDumper):
    def ignore_aliases(self,data):return True
HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'delay-r1-validation.json').read_text())
if not data['capture_passed']:raise RuntimeError('Measurement capture did not finish')
for model in ['s5kgw1','imx471']:
    delays=data['sensors'][model]['observed_delays']
    if not all(d['usable_domains']>0 and d['first_changed_offsets']==[2] and d['plateau_offsets']==[2] for d in delays.values()):raise RuntimeError('Review '+model+' timing')
    p=HERE/(model+'.yaml');profile=yaml.safe_load(p.read_text());entry=profile['modes'][1]
    entry['sensor_controls']={**entry['match'],'exposure_delay':2,'gain_delay':2}
    entry['agc']=copy.deepcopy(profile['modes'][0]['agc'])
    if model=='imx471':entry['agc']['AeExposureMode']['ExposureNormal']['exposureTime']=[100,12000,17000]
    p.write_text('# Experimental mode catalog, not per-unit IQ calibration.\n'+yaml.dump(profile,Dumper=PlainYaml,sort_keys=False))
print('Enabled measured main16:9/front1928 modes; retained per-mode exposure policy.')
