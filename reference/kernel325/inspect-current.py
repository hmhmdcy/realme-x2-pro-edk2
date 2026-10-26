from pathlib import Path
import json,shlex
import host
code='''
from pathlib import Path
import hashlib,json,subprocess
result={}
for name in ['s5kgw1','lc898219xi']:
 p=Path('/sys/module')/name
 result[name]=dict(refcount=(p/'refcnt').read_text().strip(),holders=[p.name for p in (p/'holders').iterdir()],
  devices=[dict(name=d.name,power=(d/'power/runtime_status').read_text().strip()) for d in (Path('/sys/bus/i2c/drivers')/name).iterdir() if (d/'of_node').exists()])
target=Path(subprocess.check_output(['modinfo','-n','s5kgw1'],text=True).strip()).resolve()
result['module_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
result['module_note_sha256']=hashlib.sha256(Path('/sys/module/s5kgw1/notes/.note.gnu.build-id').read_bytes()).hexdigest()
print(json.dumps(result))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);(host.PRIVATE/'post-r1-current-private.json').write_bytes(q.stdout);print(q.stdout.decode())
