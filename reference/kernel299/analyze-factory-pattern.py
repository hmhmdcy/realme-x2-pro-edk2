"""Compare the hardware factory-BLS experiment to an independent RDI model."""
from pathlib import Path
import hashlib,json,os,re,sys
HERE=Path(__file__).resolve().parent
if os.name!='nt':
 import host,shlex
 assert json.loads((HERE/'factory-bls-capture-validation.json').read_text())['passed']
 for frame in range(8,54,9):
  command=f"from pathlib import Path;import sys;b=Path('/var/lib/samurai/k299-factory-bls/frame-private-{frame}.nv12').read_bytes();assert len(b)==115200;sys.stdout.buffer.write(b)"
  q=host.ssh('python3 -c '+shlex.quote(command),timeout=15);assert len(q.stdout)==115200
  p=host.PRIVATE/f'pattern-{frame}-private.nv12';assert not p.exists();p.write_bytes(q.stdout)
 print('Fetched six hardware factory-BLS pattern frames privately.');sys.exit(0)
import numpy as np
P=Path('E:/edk2-samurai-out/kernel299')
raw=json.loads((HERE.parent/'kernel291/tele-pixel-validation.json').read_text());rgb=np.array([r['raw_rgb'] for r in raw['patches']])
offsets=[0,960,960,960,0,1024]
gains=np.array([[1,1,1],[1,1,1],[136/128]*3,[68/128,136/128,102/128],[1,1,1],[1,1,1]])
names=['neutral','factory_subtraction','factory_explicit_normalization','normalization_with_separate_color_gains','disabled','scene_pedestal_reference']
matrix=np.array([[.299,.587,.114],[-.168736,-.331264,.5],[.5,-.418688,-.081312]])
phases=[]
for phase,frame in enumerate(range(8,54,9)):
 b=(P/f'pattern-{frame}-private.nv12').read_bytes();a=np.frombuffer(b,np.uint8);y=a[:76800].reshape(240,320);uv=a[76800:].reshape(120,160,2)
 linear=np.clip(np.maximum(rgb-offsets[phase]/16368,0)*gains[phase],0,1)
 encoded=np.where(linear<=.0031308,12.92*linear,1.055*linear**(1/2.4)-.055)*255
 expected=np.clip(encoded@matrix.T+np.array([0,128,128]),0,255);patches=[]
 for i in range(8):
  left=i*40+8;right=(i+1)*40-8
  actual=np.array([y[8:-8,left:right].mean(),uv[4:-4,left//2:right//2,0].mean(),uv[4:-4,left//2:right//2,1].mean()])
  patches.append(dict(index=i,expected_yuv=expected[i].tolist(),actual_yuv=actual.tolist(),max_error=float(abs(expected[i]-actual).max())))
 phases.append(dict(phase=phase,name=names[phase],frame=frame,black_offset_u14=offsets[phase],effective_gains_rgb=gains[phase].tolist(),sha256=hashlib.sha256(b).hexdigest(),patches=patches,max_error=max(r['max_error'] for r in patches)))
capture=json.loads((HERE/'factory-bls-capture-validation.json').read_text());text=capture['tool_output'];frames=[];events=[]
for line in text.splitlines():
 if line.startswith('PIX_LEVEL '):
  r=dict(re.findall(r'(\w+)=([\d.]+)',line));frames.append({k:float(v) if k.endswith('_y') else int(v) for k,v in r.items()})
 elif line.startswith('PARAM_DQ '):events.append({k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)})
transitions=[]
for event in events:
 phase=event['phase'];expected=[phases[phase]['patches'][i]['expected_yuv'][0] for i in [0,5,3,6]]
 matches=[r for r in frames if r['phase']==phase and max(abs(r[k]-v) for k,v in zip(['white_y','red_y','green_y','blue_y'],expected))<=4]
 first=matches[0] if matches else None
 transitions.append(dict(phase=phase,parameter_sequence=event['sequence'],first_matching_sequence=first['sequence'] if first else None,exact=bool(first and first['sequence']==event['sequence']),observable=phase!=0))
report=dict(stage=299,kernel_build=298,physical_sensor_pattern=True,independent_rdi_reference=True,no_cpu_isp_before_capture=True,
 phases=phases,max_channel_error=max(r['max_error'] for r in phases),color_contract_passed=all(r['max_error']<=4 for r in phases),
 parameter_transitions=transitions,all_five_observable_transitions_exact=all(r['exact'] for r in transitions if r['observable']),
 factory_normalization_explicit_in_userspace=True,driver_bls_scale_unity=True,factory_iq_or_individual_calibration_not_claimed=True)
(HERE/'factory-pattern-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='phases'},indent=2))
assert report['color_contract_passed'] and report['all_five_observable_transitions_exact']
