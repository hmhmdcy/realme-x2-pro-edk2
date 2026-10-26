"""Emit reviewable common-driver patches and inspect available DT validation."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import shutil
import subprocess

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel267')
K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
inputs=[('imx319.c',R.parent/'kernel235/imx319.c','drivers/media/i2c/imx319.c'),
 ('qcom-pm8008.c',R.parent/'kernel235/qcom-pm8008.c','drivers/mfd/qcom-pm8008.c'),
 ('qcom-pm8008-regulator.c',K/'drivers/regulator/qcom-pm8008-regulator.c','drivers/regulator/qcom-pm8008-regulator.c')]
results={}
for name,base,path in inputs:
    text='Subject: [PATCH] '+path+': use common camera resources\n\n---\n'
    text+=''.join(difflib.unified_diff(base.read_text().splitlines(True),(R/name).read_text().splitlines(True),fromfile='a/'+path,tofile='b/'+path))
    patch=R/(name+'.patch');patch.write_text(text)
    q=subprocess.run([str(K/'scripts/checkpatch.pl'),'--no-signoff',str(patch)],capture_output=True)
    (P/(name+'-checkpatch-private.log')).write_bytes(q.stdout+q.stderr)
    results[name]=dict(exit=q.returncode,summary=q.stdout.decode().split('total:')[-1].splitlines()[0])
print(json.dumps(dict(checkpatch=results,dt_schema_available=importlib.util.find_spec('dtschema') is not None,dt_validate=shutil.which('dt-validate'))))
