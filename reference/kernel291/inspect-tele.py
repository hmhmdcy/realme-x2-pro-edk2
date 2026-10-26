"""Read telephoto controls and mode before reusing the standard physical path."""
from pathlib import Path
import json
import host
ROOT=Path(__file__).resolve().parent
code=r'''
import json,re,subprocess
graph=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],text=True)
entity=next(x for x in graph.split('- entity ') if 's5k3m5 ' in x.splitlines()[0]);node=re.search(r'device node name (\S+)',entity)[1]
q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls-menus','--get-subdev-fmt','pad=0'],capture_output=True,text=True);assert q.returncode==0
print(json.dumps(dict(stage=291,sensor='s5k3m5',node=node,stdout=q.stdout)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);data=json.loads(q.stdout)
(ROOT/'tele-controls-validation.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data,indent=2))
