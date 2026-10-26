from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
p=k/'drivers/media/i2c/imx471.c';text=p.read_text()
text=text.replace('error_sleep_pins:\n\tpinctrl_pm_select_sleep_state(dev);','error_sleep_pins:\n\tif (pinctrl_pm_select_sleep_state(dev))\n\t\tdev_err(dev, "failed to restore sleep pins\\n");')
p.write_text(text)
schema=k/'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml';assert not schema.exists() or schema.read_bytes()==(ref/schema.name).read_bytes();schema.write_bytes((ref/schema.name).read_bytes())
patch=subprocess.check_output(['git','diff','--','drivers/media/i2c/imx471.c'],cwd=k,text=True)
new=subprocess.run(['git','diff','--no-index','--','/dev/null',str(schema)],capture_output=True,text=True);assert new.returncode==1
binding_patch=new.stdout.replace('a'+str(k)+'/', 'a/').replace('b'+str(k)+'/', 'b/')
(ref/'imx471-of-supplies-and-pinctrl.patch').write_text(patch);(ref/'imx471-device-tree-binding.patch').write_text(binding_patch)
checks=[subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=data,capture_output=True,text=True) for data in [patch,binding_patch]]
(out/'imx471-checkpatch-private.log').write_text('\n'.join(c.stdout+c.stderr for c in checks))
source=json.loads((ref/'imx471-source-validation.json').read_text());source.update(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binding_sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),checkpatch_exit=max(c.returncode for c in checks))
(ref/'imx471-source-validation.json').write_text(json.dumps(source,indent=2)+'\n');print('\n'.join(c.stdout[-1000:] for c in checks))
