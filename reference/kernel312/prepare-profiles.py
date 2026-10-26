"""Create catalogs from measured310 profiles; new modes start without assumed delay."""
from pathlib import Path
import yaml
class PlainYaml(yaml.SafeDumper):
    def ignore_aliases(self,data):return True
HERE=Path(__file__).resolve().parent
new={'s5kgw1':(4608,2592,1920000000,17824,3584),'imx471':(1928,1088,387200000,5120,1308)}
for model in ['s5kgw1','imx471','imx319','s5k3m5']:
    profile=yaml.safe_load((HERE.parent/'kernel311'/(model+'.yaml')).read_text())
    profile.pop('version');profile.pop('sensor_model')
    timing=profile['sensor_controls']
    match={k:timing[k] for k in ['width','height','pixel_rate','line_length','frame_length']}
    modes=[{'match':match,**profile}]
    if model in new:
        width,height,rate,line,frame=new[model]
        another={k:v for k,v in profile.items() if k not in ['sensor_controls','agc']}
        modes.append({'match':dict(width=width,height=height,pixel_rate=rate,line_length=line,frame_length=frame),**another})
        measure={k:v for k,v in another.items() if k!='awb'}
        (HERE/(model+'-measure.yaml')).write_text(yaml.dump({'version':1,'sensor_model':model,**measure},Dumper=PlainYaml,sort_keys=False))
    (HERE/(model+'.yaml')).write_text('# Experimental mode catalog, not per-unit IQ calibration.\n'+yaml.dump({'version':2,'sensor_model':model,'modes':modes},Dumper=PlainYaml,sort_keys=False))
print('Prepared four catalogs for six advertised modes; new mode delays not assumed.')
