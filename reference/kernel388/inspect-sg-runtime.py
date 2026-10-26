from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code="""from pathlib import Path
import hashlib,json,subprocess
names=['qcom_camss','videobuf2_dma_sg']
result={}
for name in names:
 module=Path('/sys/module',name);path=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 result[name]=dict(path=str(path),file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),note_sha256=hashlib.sha256((module/'notes/.note.gnu.build-id').read_bytes()).hexdigest(),
  refcount=int((module/'refcnt').read_text()),holders=sorted(p.name for p in (module/'holders').iterdir()))
print(json.dumps(result))
"""
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);(host.PRIVATE/'sg-runtime-baseline-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert d['videobuf2_dma_sg']['holders']==['qcom_camss']
print(json.dumps(d,indent=2))
