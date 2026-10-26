from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai/k305-geometry-r2')
print(json.dumps(dict(enumeration=(root/'libcamera-enumeration-private.log').read_text(),
 geometry=(root/'geometry-private.log').read_text(),cam_help=(root/'cam-help-private.txt').read_text())))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=15)
d=json.loads(q.stdout)
(host.PRIVATE/'rollback-inspection-private.json').write_text(json.dumps(d,indent=2)+'\n')
print(d['enumeration'])
print(d['cam_help'])
