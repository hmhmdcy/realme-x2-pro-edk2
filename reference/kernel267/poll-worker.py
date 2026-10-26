"""Read a recorded native worker; never relaunch an unknown operation."""
from pathlib import Path
import json
import sys
import host

name=sys.argv[1];assert name in ['module-transaction','quiesce','native-cam']
code="""
from pathlib import Path
import json
p=Path('/var/lib/samurai/k267-NAME')
s=json.loads((p/'state-private.json').read_text());report=dict(state=s)
if (p/'summary.json').exists():report['summary']=json.loads((p/'summary.json').read_text())
if (p/'failure-private.txt').exists():report['failure']=(p/'failure-private.txt').read_text()[-4000:]
print(json.dumps(report))
""".replace('NAME',name)
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/(name+'-poll-private.json')).write_bytes(q.stdout)
print(q.stdout.decode())
if json.loads(q.stdout)['state']['terminal']:
    assert json.loads(q.stdout)['state']['exit_code']==0
    (Path(__file__).parent/(name+'-validation.json')).write_text(json.dumps(json.loads(q.stdout)['summary'],indent=2)+'\n')
