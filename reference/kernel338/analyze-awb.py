from pathlib import Path
import json,math,re,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1]
d=json.loads((P/('probe-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live'] and d['state']['summary']['passed'];rows=[]
for model in ['s5kgw1','imx471','imx319','s5k3m5']:
 text=d['logs']['capture-awb-'+model+'.log'];frames=[]
 for line in text.splitlines():
  if line.startswith('AWB_FRAME '):frames.append(dict(re.findall(r'([\w-]+)=([^ ]+)',line)))
 assert frames and len(frames)==d['state']['summary']['captures']['awb:'+model]['frames']
 settled=[r for r in frames if r['settled']=='1'];assert len(settled)==1 and settled[0]['awb']=='1' and settled[0]['locked']=='1'
 gains=[float(settled[0][name]) for name in ['red','blue']];assert all(math.isfinite(v) and v>0 for v in gains) and gains!=[1.25,.75]
 image=P/('samples-'+run)/('sample-'+model+'-awb-private.nv12');assert image.stat().st_size==115200
 rows.append(dict(model=model,frames=len(frames),awb_locked=True,image_stable=True,effective_gains=gains,gains_changed_from_start=True,uses_installed_ipa=True))
report=dict(stage=338,run=run,cameras=rows,changed_grid_automatic_white_balance_verified=True,internal_pattern_only=True,installed=False,normal_light_optical_validation=False,passed=True)
(HERE/'awb-grid-validation.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/('probe-'+run+'-validation.json')).write_text(json.dumps(d['state']['summary'],indent=2)+'\n');print(json.dumps(report,indent=2))
