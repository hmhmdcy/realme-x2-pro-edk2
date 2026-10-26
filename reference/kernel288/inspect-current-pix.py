"""Disambiguate the old named PIX entity from a real processed capture path."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
import json,subprocess
from pathlib import Path
rows={}
for entity in ['msm_vfe0_pix','msm_vfe0_video3','msm_csid0']:
 p=subprocess.run(['media-ctl','-d','/dev/media0','-e',entity],text=True,capture_output=True,timeout=6)
 if p.returncode:rows[entity]=dict(present=False);continue
 node=p.stdout.strip()
 args=['v4l2-ctl','--device',node,'--list-formats-ext'] if entity=='msm_vfe0_video3' else ['v4l2-ctl','--device',node,'--list-ctrls-menus']
 q=subprocess.run(args,text=True,capture_output=True,timeout=6)
 rows[entity]=dict(present=True,node=node,query_exit=q.returncode,output=q.stdout,error=q.stderr)
Path('/var/lib/samurai/k288-current-pix-tools-private.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
data=json.loads(q.stdout)
(host.PRIVATE/'current-pix-tools-private.json').write_bytes(q.stdout)
report=dict(stage=288,read_only=True,not_deployed=True,entity_queries=data,
            entity_name_alone_does_not_prove_isp=True)
(ROOT/'current-pix-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
