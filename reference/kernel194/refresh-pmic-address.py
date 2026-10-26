from pathlib import Path
import subprocess,hashlib,json
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel194');report=json.loads((ref/'pmic-address-source-validation.json').read_text());results=[]
for name,filename in [('drivers/mfd/qcom-pm8008.c','pm8008-initial-address.patch'),('Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml','pm8008-initial-address-binding.patch')]:
 patch=subprocess.check_output(['git','diff','--',name],cwd=k,text=True);(ref/filename).write_text(patch)
 c=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True,text=True);(out/(filename+'-checkpatch-private.log')).write_text(c.stdout+c.stderr);results.append(c.returncode);print(c.stdout[-2000:])
report['checkpatch_exit']=max(results);report['source_sha256']=hashlib.sha256((k/'drivers/mfd/qcom-pm8008.c').read_bytes()).hexdigest();report['binding_sha256']=hashlib.sha256((k/'Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml').read_bytes()).hexdigest();(ref/'pmic-address-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
