"""Observe normal GW1 AE warmup and retain early/late JPEGs privately."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'main-capture-validation.json').read_text())['all_passed']
t=ast.parse((R.parent/'kernel270/capture-two-rear-jpegs.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets));code=ast.literal_eval(n.value)
for a,b in [('k270-two-rear-jpeg-r1','k273-main-ae-r1'),('k270-work','k273-work'),('range(36)','range(600)'),('timeout=35','timeout=100'),('stage=270','stage=273'),
 ("('cam-front-','cam-rear-','cam-tele-')","('cam-front-','cam-rear-','cam-tele-','cam-main-')"),
 ("['7-0010','8-002d','9-0010']","['6-0010','7-0010','8-002d','9-0010']"),
 ('video/x-raw,format=RGBx !','video/x-raw,format=RGBx,width=1280,height=960 !')]:
 code=code.replace(a,b)
a="for which,ident in [('wide','/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10'),('tele','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d')]:"
assert a in code;code=code.replace(a,"for which,ident in [('main','/base/soc@0/cci@ac4a000/i2c-bus@0/camera@10')]:").replace("len(state['runs'])==2","len(state['runs'])==1")
code=code.replace('time.sleep(1)','time.sleep(3)').replace('frames=[];image=None','frames=[];image=None;photos=[]')
a="  frames.append(dict(pts=int(buffer.pts),bytes=len(image)))"
b=a+"\n  if i+1 in [36,180,600]:\n   p=out/(which+'-'+str(i+1)+'-private.jpg');p.write_bytes(image)\n   photos.append(dict(frame=i+1,bytes=len(image),sha256=hashlib.sha256(image).hexdigest(),path=str(p)))"
assert a in code;code=code.replace(a,b).replace("path=str(target))","path=str(target),photos=photos)")
response=host.PRIVATE/'main-ae-response-private.log';assert not response.exists();response.write_bytes(b'SUBMISSION INTENT: inspect k273-main-ae-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=125,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect the same capture process before retry'
d=json.loads(q.stdout)
for row in d['runs']:
 row.pop('path',None)
 for photo in row.get('photos',[]):photo.pop('path',None)
 pts=row.pop('pts',None)
 if pts:row['first_pts']=pts[0]['pts'];row['last_pts']=pts[-1]['pts']
(R/'main-ae-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
