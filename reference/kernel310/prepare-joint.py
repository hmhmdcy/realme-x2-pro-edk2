"""Use measured main/front delays, keeping sensor policy in mode profiles."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
evidence=json.loads((HERE/'delay-r1-validation.json').read_text())
if not evidence['capture_passed']:raise RuntimeError('Measurement capture failed')
timings={'s5kgw1':(4608,3456,1920000000,17824,3584,32),
         'imx471':(2304,1728,326400000,2560,2124,16)}
agc=(HERE.parent/'kernel309/s5k3m5.yaml').read_text().split('agc:',1)[1]
for model,(width,height,rate,line,frame,maxgain) in timings.items():
    delays=evidence['sensors'][model]['observed_delays']
    if not all(d['usable_domains'] and d['first_changed_offsets']==[2] and d['plateau_offsets']==[2] for d in delays.values()):
        raise RuntimeError('Measured delays require review: '+model)
    profile=(HERE.parent/'kernel309'/(model+'.yaml')).read_text().replace('...\n','')
    timing=f'''sensor_controls:
  width: {width}
  height: {height}
  pixel_rate: {rate}
  line_length: {line}
  frame_length: {frame}
  exposure_delay: 2
  gain_delay: 2
'''
    profile=profile.replace('awb:',timing+'awb:')
    profile+='agc:'+agc.replace('16.0',str(maxgain)+'.0')
    (HERE/(model+'.yaml')).write_text(profile)
for model in ['imx319','s5k3m5']:
    (HERE/(model+'.yaml')).write_text((HERE.parent/'kernel309'/(model+'.yaml')).read_text())
s=(HERE.parent/'kernel309/camera-smoke.cpp').read_text()
s=s.replace('int32_t previousExposure=0; float previousGain=0;',
            'int32_t previousExposure=0; float previousGain=0; float maximumGain=1;')
s=s.replace('*analogue > 16','*analogue > maximumGain + .0001f')
s=s.replace('if (config->at(0).stride != 320) return 6;',
            'if (config->at(0).stride != 320) return 6;\n    capture.maximumGain=camera->controls().at(&controls::AnalogueGain).max().get<float>();')
s=s.replace('int32_t(automaticAe ? 5000 : 30000)',
            'int32_t(automaticAe ? (epoch ? 30000 : 5000) : 30000)')
s=s.replace('automaticAe ? 2.0f : 8.0f',
            'automaticAe ? (epoch ? std::min(16.0f,capture.maximumGain) : 2.0f) : 8.0f')
(HERE/'camera-smoke.cpp').write_text(s)
print('Prepared mode-scoped measured timing and joint AE/AWB from low/high initial EV.')
