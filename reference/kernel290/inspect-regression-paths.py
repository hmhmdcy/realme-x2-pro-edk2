"""Verify which processing path the new kernel's standard camera regression actually used."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai/k290-four-camera-regression-r1')
result={}
for n,name in [(0,'front'),(1,'main'),(2,'wide'),(3,'tele')]:
 text=(r/(str(n)+'-stderr-private.log')).read_text(errors='replace')
 lines=[l for l in text.splitlines() if any(s in l.lower() for s in ['configuring streams','software isp','softwareisp','simple','configured format'])]
 result[name]=lines
print(json.dumps(result))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=15)
data=json.loads(q.stdout)
(ROOT/'regression-path-validation.json').write_text(json.dumps(dict(stage=290,camera_log_lines=data),indent=2)+'\n')
print(json.dumps(data,indent=2))
