from pathlib import Path
import hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel194');out.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={n:sha(k/n) for n in subprocess.check_output(['git','diff','--name-only'],cwd=k,text=True).splitlines()};assert len(before)==16
p=k/'drivers/media/i2c/imx471.c';old=p.read_text();(out/'imx471-before-private.c').write_text(old)
text=old.replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/of.h>\n#include <linux/pinctrl/consumer.h>')
text=text.replace('static const char * const imx471_supply_name[] = {\n\t"vana",\n};','static const char * const imx471_supply_name[] = {\n\t"vana", /* 2.8V analog */\n\t"vdig", /* 1.05V core */\n\t"vif",  /* 1.8V interface */\n};')
assert text!=old and text.count('"vdig"')==1
old_on='''	ret = regulator_bulk_enable(ARRAY_SIZE(imx471_supply_name),
				    sensor->supplies);
	if (ret < 0) {
		dev_err(dev, "failed to enable regulators: %d\\n", ret);
		return ret;
	}
'''
new_on='''	ret = pinctrl_pm_select_default_state(dev);
	if (ret)
		return dev_err_probe(dev, ret, "failed to select active pins\\n");

	ret = regulator_bulk_enable(ARRAY_SIZE(imx471_supply_name),
				    sensor->supplies);
	if (ret < 0) {
		dev_err(dev, "failed to enable regulators: %d\\n", ret);
		goto error_sleep_pins;
	}
'''
assert text.count(old_on)==1;text=text.replace(old_on,new_on)
old_err='''		dev_err(dev, "failed to enable imaging clock: %d\\n", ret);
		return ret;
	}'''
assert text.count(old_err)==1;text=text.replace(old_err,old_err.replace('\t\treturn ret;','\t\tgoto error_sleep_pins;'))
start=text.index('static int imx471_power_on(');end=text.index('\nstatic int imx471_enable_stream',start);part=text[start:end]
assert part.endswith('\treturn 0;\n}\n')
part=part[:-len('\treturn 0;\n}\n')]+'''	return 0;

error_sleep_pins:
	pinctrl_pm_select_sleep_state(dev);
	return ret;
}
''';text=text[:start]+part+text[end:]
start=text.index('static int imx471_power_off(');end=text.index('\nstatic int imx471_power_on',start);part=text[start:end];assert part.count('\treturn 0;')==1;part=part.replace('\treturn 0;','\treturn pinctrl_pm_select_sleep_state(dev);');text=text[:start]+part+text[end:]
needle='MODULE_DEVICE_TABLE(acpi, imx471_acpi_ids);';assert text.count(needle)==1
text=text.replace(needle,needle+'''

static const struct of_device_id imx471_of_match[] = {
	{ .compatible = "sony,imx471" },
	{ /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, imx471_of_match);''')
needle='\t\t.acpi_match_table = ACPI_PTR(imx471_acpi_ids),';assert text.count(needle)==1;text=text.replace(needle,needle+'\n\t\t.of_match_table = imx471_of_match,');p.write_text(text)
assert all(sha(k/n)==h for n,h in before.items())
patch=subprocess.check_output(['git','diff','--','drivers/media/i2c/imx471.c'],cwd=k,text=True);(ref/'imx471-of-supplies-and-pinctrl.patch').write_text(patch)
check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True,text=True);(out/'imx471-checkpatch-private.log').write_text(check.stdout+check.stderr)
report=dict(stage=194,base_source_sha256=hashlib.sha256(old.encode()).hexdigest(),source_sha256=sha(p),prior16_tracked_sources=before,checkpatch_exit=check.returncode,upstream_proposal_message_ids=['20260805-imx471-v1-2-7be79f539ed8@mainlining.org','20260805-imx471-v1-3-7be79f539ed8@mainlining.org'],of_match_added=True,three_supplies=['vana','vdig','vif'],optional_pinctrl_sleep_restored_on_enable_errors=True,hardware_deployed=False)
(ref/'imx471-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({n:v for n,v in report.items() if n!='prior16_tracked_sources'}));print(check.stdout[-1500:])
