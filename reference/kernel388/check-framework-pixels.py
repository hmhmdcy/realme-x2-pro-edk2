"""Reuse the independent image oracle against the final owner-API experiment."""
from pathlib import Path
import base64,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'framework-runtime-validation.json').read_text())['passed']
code="""from pathlib import Path
import base64,json
root=Path('/var/lib/samurai/k388-framework-r1/native')
state=json.loads((root/'state.json').read_text());assert state['terminal'] and state['passed']
print(json.dumps({p.name:base64.b64encode(p.read_bytes()).decode() for p in root.glob('case-*-last-private.nv12')}))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=30).stdout)
out=P/'framework-collected-r1/native'
assert len(d)==4
for name,value in d.items():(out/name).write_bytes(base64.b64decode(value))
script=(HERE.parent/'kernel386/check-pixels.py').read_text()
start=script.index("runtime=json.loads(");end=script.index("client=runtime['client_report']")
script=script[:start]+"runtime=json.loads((P/'framework-collected-r1/native/state.json').read_text())\nassert runtime['passed'] and runtime['terminal']\n"+script[end:]
script=script.replace('collected-r4','framework-collected-r1/native').replace("stage=386,run='r4'","stage=388,run='framework-r1'")
script=script.replace("b'\\xa5'*(stride-w)","b'\\xa7'*(stride-w)")
script=script.replace('zero_copy_not_claimed=True,libcamera_pipeline_not_yet_integrated=True','direct_dma_without_core_image_copy=True,final_owner_api_runtime=True')
script=script.replace("HERE/'pixels-validation.json'","HERE/'framework-pixels-validation.json'")
exec(compile(script,str(HERE/'framework-pixels-generated.py'),'exec'),globals())
