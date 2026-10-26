"""Inspect before/after AF samples selected by actual metadata, not camera timing guesses."""
from pathlib import Path
import base64,json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r1'
sys.path.insert(0,str(HERE.parent/'kernel423'));from nv12 import render
assert json.loads((HERE/'hardware-validation.json').read_text())['passed']
selected={};meta={}
for name in ['scene-factory-af','scene-factory-af-isolated']:
 rows=[dict(re.findall(r'([a-z-]+)=([^ ]+)',l)) for l in (root/(name+'.log')).read_text().splitlines() if 'ADAPT_FRAME ' in l]
 before=[r for r in rows if r['phase']=='0'][-1];after=rows[-1]
 selected[name]=int(before['sequence']);meta[name]=(before,after)
code='''from pathlib import Path
import base64,json
root=Path('/var/lib/samurai/k424-tone-r1');selected=SELECTED
assert json.loads((root/'state.json').read_text())['terminal']
result={}
for name,sequence in selected.items():
 p=root/name/('frame-'+str(sequence)+'.nv12');raw=p.read_bytes();assert len(raw)==460800
 result[name]=base64.b64encode(raw).decode()
print(json.dumps(result))
'''.replace('SELECTED',repr(selected))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);(P/'before-af-fetch-private.json').write_bytes(q.stdout);data=json.loads(q.stdout)
def metrics(raw):
 y=raw[:307200];mean=sum(y)/len(y);gradient=0;count=0
 # Same central region for both images; normalized by its own mean signal.
 signal=0
 for row in range(120,360):
  for x in range(160,480):
   at=row*640+x;signal+=y[at];gradient+=(y[at+1]-y[at])**2+(y[at+640]-y[at])**2;count+=1
 center=signal/count
 return dict(mean_y=mean,central_mean_y=center,central_squared_gradient=gradient/count,normalized_gradient=(gradient/count)/(max(center-16,1)**2))
results=[]
for name,encoded in data.items():
 before=base64.b64decode(encoded);after=next((root/name).glob('*.nv12')).read_bytes()
 (P/(name+'-before-af-private.nv12')).write_bytes(before)
 render(before,P/(name+'-before-af-private.png'));render(after,P/(name+'-after-af-private.png'))
 a,b=meta[name];results.append(dict(capture=name,before_sequence=int(a['sequence']),after_sequence=int(b['sequence']),before_af_state=int(a['af-state']),after_af_state=int(b['af-state']),
  before_fom=int(a['focus-fom']),after_fom=int(b['focus-fom']),before=metrics(before),after=metrics(after),
  no_test_pattern=True,no_app_tone_filter=True,scene_dependent_focus_evidence_not_absolute_optical_calibration=True))
r=dict(stage=424,before_selected_from_last_ae_warmup_frame=True,after_selected_from_final_completed_frame=True,rows=results,passed=True)
(HERE/'scenes-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
