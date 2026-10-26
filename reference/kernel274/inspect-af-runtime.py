from pathlib import Path
import json
import host
code="""
import importlib.util,json,subprocess
from pathlib import Path
print(json.dumps(dict(pillow=importlib.util.find_spec('PIL') is not None,numpy=importlib.util.find_spec('numpy') is not None,
 cam_help=subprocess.check_output(['cam','--help'],text=True),i2c_name=Path('/sys/bus/i2c/devices/i2c-6/name').read_text().strip())))
"""
q=host.ssh('python3 -',input=code.encode(),timeout=15);d=json.loads(q.stdout)
(host.PRIVATE/'af-runtime-utilities-private.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
