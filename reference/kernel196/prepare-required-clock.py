from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel196');p=k/'drivers/media/i2c/imx471.c';s=p.read_text();r=json.loads((ref/'imx471-source-validation.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==r['source_sha256'];assert s.count('devm_v4l2_sensor_clk_get(sensor->dev, NULL)')==2
(out/'imx471-before-required-clock-private.c').write_bytes(p.read_bytes());s=s.replace('devm_v4l2_sensor_clk_get(sensor->dev, NULL)','imx471_get_sensor_clock(sensor->dev)')
needle='static int imx471_check_hwcfg(';i=s.index(needle);s=s[:i]+'''static struct clk *imx471_get_sensor_clock(struct device *dev)
{
	/* OF describes a required hardware clock; ACPI may provide a fixed rate. */
	if (dev_of_node(dev))
		return devm_clk_get(dev, NULL);
	return devm_v4l2_sensor_clk_get(dev, NULL);
}

'''+s[i:];p.write_text(s);patch=subprocess.check_output(['git','diff','--','drivers/media/i2c/imx471.c'],cwd=k,text=True);(ref/'imx471-of-ordered-power.patch').write_text(patch);c=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True,text=True);(out/'imx471-clock-checkpatch-private.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stdout
r.update(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),of_uses_required_devm_clk_get=True,acpi_clock_helper_preserved=True);(ref/'imx471-source-validation.json').write_text(json.dumps(r,indent=2)+'\n')
# Retain the previous native module and use separate build logs.
old=out/'imx471.ko';old.rename(out/'imx471-before-required-clock-private.ko');s=(ref/'build-imx471-module.py').read_text().replace('olddefconfig-r3','olddefconfig-r4').replace('module-build-r3','module-build-r4');s=s.replace("cci=out/'v4l2-cci.ko';assert not cci.exists();", "cci=out/'v4l2-cci-r4.ko';assert not cci.exists();");(ref/'build-imx471-clock-module.py').write_text(s)
print(json.dumps(r))
