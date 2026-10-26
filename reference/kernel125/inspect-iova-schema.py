from pathlib import Path
import runpy,os
r=Path('/mnt/e/RealmeX2Pro edk2');runpy.run_path(str(r/'reference/kernel118/ensure-build-volume.py'))
p='/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/bin/python'
code="""import dtschema,json,pathlib,inspect
v=dtschema.DTValidator(['/mnt/e/edk2-samurai-out/kernel125/schema-test/processed-camss-private.json'])
for key,value in v.schemas.items():
 if 'reserved-memory/reserved-memory.yaml' in key:print(key,json.dumps(value,indent=2))
print(inspect.getsource(v.iter_errors))
"""
os.execv(p,[p,'-c',code])
