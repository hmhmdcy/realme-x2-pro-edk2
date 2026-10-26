from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel137'
out = Path('/mnt/e/edk2-samurai-out/kernel137')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
assert os.geteuid() == 0 and not out.exists()
out.mkdir(mode=0o700)
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha((k / 'arch/arm64/boot/Image').read_bytes()) == 'fa2f96eb4c0eb0b6f5b1bdaf8505f62f22744b51153635804ffa710ba83bffb1'
assert '#136 SMP PREEMPT' in subprocess.check_output(['strings', str(k / 'arch/arm64/boot/Image')], text=True)
(out / 'source136-before-private.patch').write_bytes(subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']))
changes = {}

def change(name, transform):
    old = (k / name).read_text()
    (out / (Path(name).name + '.before-private')).write_text(old)
    new = transform(old)
    assert new != old
    (k / name).write_text(new)
    changes[name] = (old, new)

def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

def mfd(text):
    text = replace(text, '''		dev_err(dev, "Failed to bring up WCD934X: err = %d\\n", ret);
		return ret;
''', '''		dev_err(dev, "Failed to bring up WCD934X: err = %d\\n", ret);
		goto err_regmap_exit;
''')
    text = replace(text, '''	ret = devm_regmap_add_irq_chip(dev, ddata->regmap, ddata->irq,
				       IRQF_TRIGGER_HIGH, 0,
				       &wcd934x_regmap_irq_chip,
				       &ddata->irq_data);''', '''	ret = regmap_add_irq_chip(ddata->regmap, ddata->irq,
				  IRQF_TRIGGER_HIGH, 0,
				  &wcd934x_regmap_irq_chip,
				  &ddata->irq_data);''')
    text = replace(text, '''		dev_err(dev, "Failed to add IRQ chip: err = %d\\n", ret);
		return ret;
''', '''		dev_err(dev, "Failed to add IRQ chip: err = %d\\n", ret);
		goto err_regmap_exit;
''')
    text = replace(text, '''		dev_err(dev, "Failed to add child devices: err = %d\\n",
			ret);
		return ret;
	}

	return ret;
}

static int wcd934x_slim_status''', '''		dev_err(dev, "Failed to add child devices: err = %d\\n", ret);
		goto err_del_irq_chip;
	}

	return 0;

err_del_irq_chip:
	regmap_del_irq_chip(ddata->irq, ddata->irq_data);
	ddata->irq_data = NULL;
err_regmap_exit:
	regmap_exit(ddata->regmap);
	ddata->regmap = NULL;
	return ret;
}

static void wcd934x_slim_status_down(struct slim_device *sdev)
{
	struct device *dev = &sdev->dev;
	struct wcd934x_ddata *ddata;

	ddata = dev_get_drvdata(dev);

	mfd_remove_devices(&sdev->dev);

	if (ddata->irq_data) {
		regmap_del_irq_chip(ddata->irq, ddata->irq_data);
		ddata->irq_data = NULL;
	}

	if (ddata->regmap) {
		regmap_exit(ddata->regmap);
		ddata->regmap = NULL;
	}
}

static int wcd934x_slim_status''')
    text = replace(text, '''	case SLIM_DEVICE_STATUS_DOWN:
		mfd_remove_devices(&sdev->dev);''', '''	case SLIM_DEVICE_STATUS_DOWN:
		wcd934x_slim_status_down(sdev);''')
    text = replace(text, '''	regulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);
	mfd_remove_devices(&sdev->dev);''', '''	regulator_bulk_disable(WCD934X_MAX_SUPPLY, ddata->supplies);
	wcd934x_slim_status_down(sdev);''')
    return text

def ngd(text):
    return replace(text, '''	if (!desc->desc) {
		dev_err(ctrl->dev, "unable to prepare channel\\n");''', '''	if (!desc->desc) {
		struct dma_chan *chan = ctrl->dma_tx_channel;
		struct dma_device *dma = chan ? chan->device : NULL;

		dev_err_once(ctrl->dev,
			     "TX DMA diagnostic: channel=%d device=%d sg=%d config_sg=%d len=%d\\n",
			     !!chan, !!dma,
			     dma && !!dma->device_prep_slave_sg,
			     dma && !!dma->device_prep_config_sg, len);
		dev_err(ctrl->dev, "unable to prepare channel\\n");''')

def bam(text):
    return replace(text, '''	async_desc = kzalloc_flex(*async_desc, desc, num_alloc, GFP_NOWAIT);
	if (!async_desc)
		return NULL;''', '''	async_desc = kzalloc_flex(*async_desc, desc, num_alloc, GFP_NOWAIT);
	if (!async_desc) {
		dev_err_once(bdev->dev,
			     "BAM DMA diagnostic: allocation failed descriptors=%u sg=%u len=%u direction=%d\\n",
			     num_alloc, sg_len, sg_dma_len(sgl), direction);
		return NULL;
	}''')

change('drivers/mfd/wcd934x.c', mfd)
change('drivers/slimbus/qcom-ngd-ctrl.c', ngd)
change('drivers/dma/qcom/bam_dma.c', bam)
patch = ''.join(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
    fromfile='a/' + name, tofile='b/' + name)) for name, (old, new) in changes.items())
(ref / 'wcd-cleanup-and-dma-diagnostics.patch').write_text(patch)
(out / 'wcd-cleanup-and-dma-diagnostics.patch').write_text(patch)
report = dict(stage=137, build_workspace_reused_after_archive=136,
    upstream_mfd_patch='https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2603.1/03387.html',
    upstream_mfd_cleanup_applied=True, first_dma_failure_diagnostics_only=True,
    dma_allocation_policy_changed=False, gpu_commands_changed=False,
    charging_configuration_writes=0, efuse_root_cause_proven=False,
    changes=[dict(path=name, before_sha256=sha(old.encode()), after_sha256=sha(new.encode()))
        for name, (old, new) in changes.items()], goal_complete=False)
(ref / 'audio-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K137_UPSTREAM_MFD_CLEANUP_AND_FIRST_DMA_FAILURE_DIAGNOSTICS_PREPARED', flush=True)
