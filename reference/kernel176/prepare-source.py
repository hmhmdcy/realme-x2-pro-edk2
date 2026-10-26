from pathlib import Path
import difflib, hashlib, json, os, shutil, subprocess

os.umask(0o077)
ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel176');out.mkdir(mode=0o700)
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
baseline=json.loads((ref.parent/'kernel175/build-package-validation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in baseline['source_sha256'].items():assert sha(k/n)==h,n
assert set(subprocess.check_output(['git','diff','--name-only'],cwd=k,text=True).splitlines())==set(baseline['source_sha256'])
names=['drivers/mfd/wcd934x.c','drivers/slimbus/core.c','include/linux/slimbus.h','drivers/slimbus/slimbus.h']
old={n:(k/n).read_text() for n in names}
for n in names[1:]:assert (k/n).read_bytes()==subprocess.check_output(['git','show','HEAD:'+n],cwd=k),n
for n in names:
    dest=out/'before-private'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(k/n,dest)
shutil.copyfile(k/'.config',out/'config-before-private')

p=k/'include/linux/slimbus.h';s=old['include/linux/slimbus.h']
s=s.replace('int slim_get_logical_addr(struct slim_device *sbdev);','int slim_get_logical_addr(struct slim_device *sbdev);\nvoid slim_report_absent(struct slim_device *sbdev);')
p.write_text(s)
p=k/'drivers/slimbus/slimbus.h';s=old['drivers/slimbus/slimbus.h'];assert s.count('void slim_report_absent(struct slim_device *sbdev);\n')==1
p.write_text(s.replace('void slim_report_absent(struct slim_device *sbdev);\n',''))
p=k/'drivers/slimbus/core.c';s=old['drivers/slimbus/core.c']
s=s.replace(' * slim_report_absent() - Controller calls this function when a device\n *\treports absent, OR when the device cannot be communicated with',
''' * slim_report_absent() - Invalidate a device address and report it absent
 *
 * Controllers call this when a device reports absent or cannot be reached.
 * A client can also use it after a hardware reset invalidates its address.''')
a=s.index('void slim_report_absent(');b=s.index('EXPORT_SYMBOL_GPL(slim_report_absent)',a)
part=s[a:b].replace('\tstruct slim_controller *ctrl = sbdev->ctrl;','\tstruct slim_controller *ctrl = sbdev->ctrl;\n\tbool was_valid;')
part=part.replace('\tsbdev->is_laddr_valid = false;\n\tmutex_unlock(&ctrl->lock);\n\tif (!ctrl->get_laddr)\n\t\tida_free(&ctrl->laddr_ida, sbdev->laddr);',
'''\twas_valid = sbdev->is_laddr_valid;
\tsbdev->is_laddr_valid = false;
\tif (was_valid && !ctrl->get_laddr)
\t\tida_free(&ctrl->laddr_ida, sbdev->laddr);
\tmutex_unlock(&ctrl->lock);''')
s=s[:a]+part+s[b:];p.write_text(s)

p=k/'drivers/mfd/wcd934x.c';s=old['drivers/mfd/wcd934x.c']
s=s.replace('\tbool up;','\tbool up;\n\tbool ready;')
a=s.index('static int wcd934x_slim_status(');b=s.index('static int wcd934x_finish_probe(',a)
part=s[a:b].replace('\tmutex_lock(&priv->lock);\n\tswitch (status)',
'''\tmutex_lock(&priv->lock);
\tif (!priv->ready) {
\t\tret = -EPROBE_DEFER;
\t\tgoto unlock;
\t}
\tswitch (status)''')
part=part.replace('\tmutex_unlock(&priv->lock);','unlock:\n\tmutex_unlock(&priv->lock);')
s=s[:a]+part+s[b:]
a=s.index('static int wcd934x_finish_probe(');b=s.index('static int wcd934x_slim_probe(',a)
s=s[:a]+'''static int wcd934x_finish_probe(struct slim_device *sdev)
{
	struct wcd934x_priv *priv = wcd934x_get_private(sdev);
	int ret;

	/* Address assignment can call device_status: do not hold priv->lock. */
	ret = slim_get_logical_addr(sdev);
	if (ret)
		return ret;

	mutex_lock(&priv->lock);
	priv->ready = true;
	ret = wcd934x_slim_status_up(sdev);
	mutex_unlock(&priv->lock);

	return ret;
}

static int wcd934x_reset_addresses(struct slim_device *sdev)
{
	struct device_node *np;
	struct slim_device *sidev;

	np = of_parse_phandle(sdev->dev.of_node, "slim-ifc-dev", 0);
	if (!np)
		return -EINVAL;
	sidev = of_slim_get_device(sdev->ctrl, np);
	of_node_put(np);
	if (!sidev)
		return -EPROBE_DEFER;

	/* Reset affects both the primary and interface logical devices. */
	slim_report_absent(sidev);
	slim_report_absent(sdev);
	put_device(&sidev->dev);

	return 0;
}

static void wcd934x_stop_action(void *data)
{
	struct slim_device *sdev = data;
	struct wcd934x_priv *priv = wcd934x_get_private(sdev);

	if (!priv)
		return;
	mutex_lock(&priv->lock);
	priv->ready = false;
	wcd934x_slim_status_down(sdev);
	mutex_unlock(&priv->lock);
}

static void wcd934x_disable_supplies(void *data)
{
	struct wcd934x_ddata *ddata = data;

	regulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);
}

'''+s[b:]
a=s.index('static int wcd934x_slim_probe(');b=s.index('static const struct slim_device_id ',a);part=s[a:b]
needle='\tret = regulator_bulk_enable(WCD934X_MAX_SUPPLY, ddata->supplies);\n\tif (ret)\n\t\treturn dev_err_probe(dev, ret, "Failed to enable supplies\\n");'
assert part.count(needle)==1
part=part.replace(needle,needle+'''
	ret = devm_add_action_or_reset(dev, wcd934x_disable_supplies, ddata);
	if (ret)
		return ret;''')
part=part.replace('''	if (IS_ERR(reset_gpio)) {
		ret = dev_err_probe(dev, PTR_ERR(reset_gpio),
				    "Failed to get reset gpio\\n");
		goto err_disable_regulators;
	}''','''	if (IS_ERR(reset_gpio))
		return dev_err_probe(dev, PTR_ERR(reset_gpio),
				     "Failed to get reset gpio\\n");''')
needle='\tdev_set_drvdata(dev, ddata);\n\tret = wcd934x_finish_probe(sdev);\n\tif (ret)\n\t\tgoto err_disable_regulators;\n\n\treturn 0;\n\nerr_disable_regulators:\n\tregulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);\n\treturn ret;'
assert part.count(needle)==1
part=part.replace(needle,'''\tret = wcd934x_reset_addresses(sdev);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "Failed to invalidate SLIM addresses\\n");

\tdev_set_drvdata(dev, ddata);
\tret = devm_add_action_or_reset(dev, wcd934x_stop_action, sdev);
\tif (ret)
\t\treturn ret;

\treturn wcd934x_finish_probe(sdev);''')
a2=part.index('static void wcd934x_slim_remove(')
part=part[:a2]+'''static void wcd934x_slim_remove(struct slim_device *sdev)
{
	wcd934x_stop_action(sdev);
}

'''
s=s[:a]+part+s[b:];p.write_text(s)

patch='''Subject: [PATCH] slimbus: refresh WCD934x addresses after reset

Invalidate primary and interface addresses after the physical reset and
defer chip setup until address assignment completes. Keep that query
outside the WCD state lock because it can notify the client. Manage
power and status cleanup even when the bus wrapper rejects a probe.
Make repeated address invalidation release an allocated address once.

---
'''
for n in names:patch+=''.join(difflib.unified_diff(old[n].splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'reset-address-and-probe-cleanup.patch').write_text(patch)
tracked=set(baseline['source_sha256'])|set(names)
report=dict(stage=176,baseline_kernel=175,modified_this_stage=names,before_sha256={n:hashlib.sha256(old[n].encode()).hexdigest() for n in names},
 source_sha256={n:sha(k/n) for n in sorted(tracked)},reset_delays_and_hardware_values_unchanged=True,
 both_logical_devices_invalidated=True,address_query_outside_wcd_lock=True,managed_status_and_power_cleanup=True,
 regmap_clock_and_jack175_port_irq174_dtb172_ucm173_preserved=True,build_and_runtime_pending=True)
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K176_SOURCE_PREPARED',flush=True)
