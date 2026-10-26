from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code='''
from pathlib import Path
import json
services={}
for name in ['pipewire','wireplumber']:
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':rows.append(dict(pid=int(p.name),uid=p.stat().st_uid))
  except (FileNotFoundError,ProcessLookupError):pass
 services[name]=rows
report=dict(stage=348,services=services,platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
print(json.dumps(report))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout)
d['passed']=all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values()) and not d['taint'] and all(v=='suspended' for v in d['platforms'].values())
(HERE/'final-state-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));assert d['passed']


