from pathlib import Path
import difflib, hashlib, json, os, shutil, subprocess

os.umask(0o077)
ref=Path(__file__).parent
out=Path('/mnt/e/edk2-samurai-out/kernel175');out.mkdir(mode=0o700)
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
baseline=json.loads((ref.parent/'kernel174/build-package-validation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in baseline['source_sha256'].items():assert sha(k/n)==h,n
assert set(subprocess.check_output(['git','diff','--name-only'],cwd=k,text=True).splitlines())==set(baseline['source_sha256'])
names=['sound/soc/qcom/samurai-audio.c','drivers/mfd/wcd934x.c']
old={n:(k/n).read_text() for n in names}
assert (k/names[1]).read_bytes()==subprocess.check_output(['git','show','HEAD:'+names[1]],cwd=k)
for n in names:
    dest=out/'before-private'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(k/n,dest)
shutil.copyfile(k/'.config',out/'config-before-private')
s=old[names[0]]
marker='static int samurai_fixup('
assert s.count(marker)==1
s=s.replace(marker,'''static void samurai_exit(struct snd_soc_pcm_runtime *rtd)
{
	struct samurai_audio_data *data = snd_soc_card_get_drvdata(rtd->card);
	struct snd_soc_dai *codec;
	int i, ret;

	if (rtd->dai_link->id != SLIMBUS_0_RX &&
	    rtd->dai_link->id != SLIMBUS_0_TX)
		return;

	for_each_rtd_codec_dais(rtd, i, codec) {
		if (data->jack_component != codec->component)
			continue;
		/* Link exit runs before the codec component is removed. */
		ret = snd_soc_component_set_jack(codec->component, NULL, NULL);
		if (ret)
			dev_err(rtd->card->dev, "WCD934x jack disconnect: %d\\n", ret);
		data->jack_component = NULL;
	}
}

static int samurai_card_remove(struct snd_soc_card *card)
{
	struct samurai_audio_data *data = snd_soc_card_get_drvdata(card);

	/* ASoC allocates a new ALSA card and jack on the next binding. */
	data->jack_created = false;
	data->jack_component = NULL;

	return 0;
}

'''+marker)
s=s.replace('\tcard->owner = THIS_MODULE;','\tcard->owner = THIS_MODULE;\n\tcard->remove = samurai_card_remove;')
s=s.replace('\t\t\tlink->init = samurai_init;','\t\t\tlink->init = samurai_init;\n\t\t\tlink->exit = samurai_exit;')
(k/names[0]).write_text(s)

s=old[names[1]].replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/mutex.h>')
marker='static const struct mfd_cell wcd934x_devices[] = {'
s=s.replace(marker,'''struct wcd934x_priv {
	struct wcd934x_ddata ddata;
	struct mutex lock;
	bool up;
};

static struct wcd934x_priv *wcd934x_get_private(struct slim_device *sdev)
{
	struct wcd934x_ddata *ddata = dev_get_drvdata(&sdev->dev);

	return container_of(ddata, struct wcd934x_priv, ddata);
}

'''+marker)
# Preserve bring-up values and stop immediately when an IO operation fails.
a=s.index('static int wcd934x_bring_up(');b=s.index('static int wcd934x_slim_status_up(',a)
lines=s[a:b].splitlines(True)
new=[]
for line in lines:
    if line.startswith('\tregmap_write('):
        new.append(line.replace('\tregmap_write(','\tret = regmap_write('))
        new.append('\tif (ret)\n\t\treturn ret;\n')
    else:new.append(line)
s=s[:a]+''.join(new)+s[b:]
a=s.index('static int wcd934x_slim_status_up(');b=s.index('static int wcd934x_slim_probe(',a)
s=s[:a]+'''static int wcd934x_slim_status_up(struct slim_device *sdev)
{
	struct device *dev = &sdev->dev;
	struct wcd934x_priv *priv = wcd934x_get_private(sdev);
	struct wcd934x_ddata *ddata = &priv->ddata;
	struct regmap *regmap;
	int ret;

	if (priv->up)
		return 0;

	regmap = regmap_init_slimbus(sdev, &wcd934x_regmap_config);
	if (IS_ERR(regmap))
		return dev_err_probe(dev, PTR_ERR(regmap), "Error allocating slim regmap\\n");
	ddata->regmap = regmap;

	ret = wcd934x_bring_up(ddata);
	if (ret) {
		dev_err(dev, "Failed to bring up WCD934X: err = %d\\n", ret);
		goto err_regmap;
	}

	ret = regmap_add_irq_chip(regmap, ddata->irq, IRQF_TRIGGER_HIGH, 0,
				 &wcd934x_regmap_irq_chip, &ddata->irq_data);
	if (ret) {
		dev_err(dev, "Failed to add IRQ chip: err = %d\\n", ret);
		goto err_regmap;
	}

	ret = mfd_add_devices(dev, PLATFORM_DEVID_AUTO, wcd934x_devices,
			      ARRAY_SIZE(wcd934x_devices), NULL, 0, NULL);
	if (ret) {
		dev_err(dev, "Failed to add child devices: err = %d\\n", ret);
		goto err_irq;
	}
	priv->up = true;

	return 0;

err_irq:
	regmap_del_irq_chip(ddata->irq, ddata->irq_data);
	ddata->irq_data = NULL;
err_regmap:
	regmap_exit(regmap);
	ddata->regmap = NULL;

	return ret;
}

static void wcd934x_slim_status_down(struct slim_device *sdev)
{
	struct wcd934x_priv *priv = wcd934x_get_private(sdev);
	struct wcd934x_ddata *ddata = &priv->ddata;

	if (!priv->up)
		return;

	/* Children must release their virtual IRQs before the domain is freed. */
	mfd_remove_devices(&sdev->dev);
	regmap_del_irq_chip(ddata->irq, ddata->irq_data);
	ddata->irq_data = NULL;
	regmap_exit(ddata->regmap);
	ddata->regmap = NULL;
	priv->up = false;
}

static int wcd934x_slim_status(struct slim_device *sdev,
			       enum slim_device_status status)
{
	struct wcd934x_priv *priv = wcd934x_get_private(sdev);
	int ret = 0;

	mutex_lock(&priv->lock);
	switch (status) {
	case SLIM_DEVICE_STATUS_UP:
		ret = wcd934x_slim_status_up(sdev);
		break;
	case SLIM_DEVICE_STATUS_DOWN:
		wcd934x_slim_status_down(sdev);
		break;
	default:
		ret = -EINVAL;
		break;
	}
	mutex_unlock(&priv->lock);

	return ret;
}

'''+s[b:]
a=s.index('static int wcd934x_slim_probe(');b=s.index('static const struct slim_device_id ',a)
part=s[a:b]
part=part.replace('\tstruct wcd934x_ddata *ddata;','\tstruct wcd934x_ddata *ddata;\n\tstruct wcd934x_priv *priv;')
part=part.replace('\tddata = devm_kzalloc(dev, sizeof(*ddata), GFP_KERNEL);\n\tif (!ddata)\n\t\treturn\t-ENOMEM;',
 '''	priv = devm_kzalloc(dev, sizeof(*priv), GFP_KERNEL);
	if (!priv)
		return -ENOMEM;
	ddata = &priv->ddata;
	ddata->dev = dev;
	mutex_init(&priv->lock);''')
part=part.replace('ret = regulator_bulk_get(dev,','ret = devm_regulator_bulk_get(dev,')
part=part.replace('\tddata->dev = dev;\n\tdev_set_drvdata(dev, ddata);','\tdev_set_drvdata(dev, ddata);')
part=part.replace('\tregulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);\n\tmfd_remove_devices(&sdev->dev);',
 '''	struct wcd934x_priv *priv = wcd934x_get_private(sdev);

	mutex_lock(&priv->lock);
	wcd934x_slim_status_down(sdev);
	mutex_unlock(&priv->lock);
	regulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);''')
assert part.count('priv = devm_kzalloc')==1 and part.count('devm_regulator_bulk_get')==1
s=s[:a]+part+s[b:]
(k/names[1]).write_text(s)

patch='''Subject: [PATCH] ASoC: samurai: release jack state on card unbind

Detach the shared WCD jack in link exit while the codec is still alive,
and reset card-specific jack flags for the next binding. Also balance
WCD MFD regmap and IRQ lifetimes on status transitions and setup failures,
make duplicate notifications idempotent and propagate bring-up IO errors.

---
'''
for n in names:patch+=''.join(difflib.unified_diff(old[n].splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
tracked=set(baseline['source_sha256'])|set(names)
report=dict(stage=175,baseline_kernel=174,modified_this_stage=names,
 before_sha256={n:hashlib.sha256(old[n].encode()).hexdigest() for n in names},
 source_sha256={n:sha(k/n) for n in sorted(tracked)},private_mfd_state_no_shared_header_change=True,
 port_irq174_dtb172_and_ucm173_preserved=True,build_and_runtime_pending=True)
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K175_SOURCE_PREPARED',flush=True)
