from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel196');out.mkdir(exist_ok=True);k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'drivers/media/i2c/imx471.c';old=p.read_text();assert hashlib.sha256(p.read_bytes()).hexdigest()=='30e94aa1274c4f3664d7be331313ddc8526cc851cafd7746f0a00b36756a321d'
assert not (out/'imx471-before196-private.c').exists();(out/'imx471-before196-private.c').write_bytes(p.read_bytes())
needle='static const char * const imx471_supply_name[] = {'
s=old.replace(needle,'''enum imx471_supply {
	IMX471_VANA,
	IMX471_VDIG,
	IMX471_VIF,
};

'''+needle)
a=s.index('static int imx471_power_off(')
helpers='''/* Keep the interface and analogue rails established before core power. */
static int imx471_enable_supplies(struct imx471 *sensor)
{
	int ret;

	if (!dev_of_node(sensor->dev))
		return regulator_bulk_enable(ARRAY_SIZE(imx471_supply_name), sensor->supplies);

	ret = regulator_enable(sensor->supplies[IMX471_VIF].consumer);
	if (ret)
		return ret;
	usleep_range(1000, 2000);
	ret = regulator_enable(sensor->supplies[IMX471_VANA].consumer);
	if (ret)
		goto disable_vif;
	usleep_range(1000, 2000);
	ret = regulator_enable(sensor->supplies[IMX471_VDIG].consumer);
	if (ret)
		goto disable_vana;
	usleep_range(1000, 2000);
	return 0;

disable_vana:
	regulator_disable(sensor->supplies[IMX471_VANA].consumer);
disable_vif:
	regulator_disable(sensor->supplies[IMX471_VIF].consumer);
	return ret;
}

static void imx471_disable_supplies(struct imx471 *sensor)
{
	if (!dev_of_node(sensor->dev)) {
		regulator_bulk_disable(ARRAY_SIZE(imx471_supply_name), sensor->supplies);
		return;
	}

	regulator_disable(sensor->supplies[IMX471_VDIG].consumer);
	regulator_disable(sensor->supplies[IMX471_VANA].consumer);
	regulator_disable(sensor->supplies[IMX471_VIF].consumer);
}

'''
s=s[:a]+helpers+s[a:]
s=s.replace('regulator_bulk_enable(ARRAY_SIZE(imx471_supply_name),\n\t\t\t\t    sensor->supplies)','imx471_enable_supplies(sensor)')
s=s.replace('regulator_bulk_disable(ARRAY_SIZE(imx471_supply_name),\n\t\t\t\t       sensor->supplies)','imx471_disable_supplies(sensor)').replace('regulator_bulk_disable(ARRAY_SIZE(imx471_supply_name),\n\t\t\t       sensor->supplies)','imx471_disable_supplies(sensor)')
p.write_text(s);patch=subprocess.check_output(['git','diff','--','drivers/media/i2c/imx471.c'],cwd=k,text=True);(ref/'imx471-of-ordered-power.patch').write_text(patch)
c=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True,text=True);(out/'imx471-checkpatch-private.log').write_text(c.stdout+c.stderr);assert c.returncode==0,c.stdout
r=dict(stage=196,source_before_sha256=hashlib.sha256(old.encode()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),checkpatch_exit=0,of_supply_order=['vif','vana','vdig'],between_enable_delay_us_min=1000,acpi_bulk_path_preserved=True,mode_table_unchanged=True,hardware_deployed=False);(ref/'imx471-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
for name in ['run-native.py','baseline.py']:
 s=(ref.parent/'kernel195'/name).read_text().replace('k195-baseline','k196-baseline').replace('stage=195','stage=196')
 (ref/name).write_text(s)
