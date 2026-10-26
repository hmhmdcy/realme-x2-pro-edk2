"""Validate local schemas with the existing isolated DT tools."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import shutil

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel267/binding-check-r2');P.mkdir(mode=0o700)
tools=Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
results={}
root=Path('/home/cy122/x2pro-linux/schema-k267')
shutil.copytree(K/'Documentation/devicetree/bindings',root/'bindings')
for name in ['qcom,pm8008.yaml','sony,imx319.yaml']:
    dest=root/'bindings'/('mfd' if name.startswith('qcom') else 'media/i2c')/name
    shutil.copyfile(R/name,dest)
    q=subprocess.run([str(tools/'dt-doc-validate'),str(dest)],capture_output=True)
    (P/(name+'-doc-private.log')).write_bytes(q.stdout+q.stderr)
    results[name]=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr))
q=subprocess.run([str(tools/'dt-mk-schema'),'-j','-o',str(root/'processed.json'),str(root/'bindings')],capture_output=True)
(P/'mk-schema-private.log').write_bytes(q.stdout+q.stderr)
results['compile']=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr))
if q.returncode==0:
    for name in ['qcom,pm8008','sony,imx319']:
        q=subprocess.run([str(tools/'dt-validate'),'-s',str(root/'processed.json'),'-l',name,
                         '/mnt/e/edk2-samurai-out/kernel267/board-build-r1/sm8150-samurai.dtb'],capture_output=True)
        (P/(name+'-dtb-private.log')).write_bytes(q.stdout+q.stderr)
        results[name+'-dtb']=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr))
(R/'binding-validation.json').write_text(json.dumps(dict(stage=267,results=results),indent=2)+'\n')
print(json.dumps(results))
