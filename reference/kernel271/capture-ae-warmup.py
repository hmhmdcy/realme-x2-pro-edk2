"""Observe normal automatic camera warm-up through native libcamerasrc/CPU JPEG."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'fractional-auto-r1-validation.json').read_text())['exit']==0
t=ast.parse((R.parent/'kernel270/capture-two-rear-jpegs.py').read_text())
n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
code=ast.literal_eval(n.value)
for a,b in [('k270-two-rear-jpeg-r1','k271-ae-warmup-r1'),('range(36)','range(600)'),('timeout=35','timeout=65'),('stage=270','stage=271')]:code=code.replace(a,b)
a="for which,ident in [('wide','/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10'),('tele','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d')]:"
b="for which,ident in [('tele','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d')]:"
assert a in code;code=code.replace(a,b).replace("len(state['runs'])==2","len(state['runs'])==1")
code=code.replace('time.sleep(1)','time.sleep(3)')
code=code.replace('frames=[];image=None','frames=[];image=None;photos=[]')
a="  frames.append(dict(pts=int(buffer.pts),bytes=len(image)))"
b=a+"\n  if i+1 in [36,180,600]:\n   p=out/(which+'-'+str(i+1)+'-private.jpg');p.write_bytes(image)\n   photos.append(dict(frame=i+1,bytes=len(image),sha256=hashlib.sha256(image).hexdigest(),path=str(p)))"
assert a in code;code=code.replace(a,b)
code=code.replace("path=str(target))", "path=str(target),photos=photos)")
response=host.PRIVATE/'ae-warmup-response-private.log';assert not response.exists()
response.write_bytes(b'SUBMISSION INTENT: inspect k271-ae-warmup-r1 if response is lost.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=90,check=False);response.write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect submitted context, do not replay'
d=json.loads(q.stdout)
for row in d['runs']:
 row.pop('path',None)
 for photo in row.get('photos',[]):photo.pop('path',None)
 pts=row.pop('pts',None)
 if pts:row['first_pts']=pts[0]['pts'];row['last_pts']=pts[-1]['pts']
(R/'ae-warmup-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
