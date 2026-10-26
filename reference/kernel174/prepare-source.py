from pathlib import Path
import difflib, hashlib, json, os, shutil, subprocess

os.umask(0o077)
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel174')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out.mkdir(mode=0o700)
baseline = json.loads((ref.parent / 'kernel172/kernel-build-validation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, digest in baseline['source_sha256'].items():
    assert sha(k / name) == digest, name
assert set(subprocess.check_output(['git','diff','--name-only'], cwd=k, text=True).splitlines()) == set(baseline['source_sha256'])
name = 'sound/soc/codecs/wcd934x.c'
p = k / name
old = p.read_text()
backup = out / 'before-private' / name
backup.parent.mkdir(parents=True)
backup.write_bytes(p.read_bytes())
shutil.copyfile(k / '.config', out / 'config-before-private')

helpers = '''/* Stream port masks have TX before RX, interrupt registers have RX first. */
static int wcd934x_slim_port_interrupts(struct wcd934x_codec *wcd,
                                      struct wcd_slim_codec_dai_data *dai,
                                      bool enable)
{
	u32 ports = (dai->sconfig.port_mask >> 16) |
		    (dai->sconfig.port_mask << 16);
	unsigned int mask, i;
	int ret, err = 0;

	for (i = 0; i < 4; i++) {
		mask = (ports >> (8 * i)) & 0xff;
		if (!mask)
			continue;
		ret = regmap_update_bits(wcd->if_regmap,
				 WCD934X_SLIM_PGD_PORT_INT_EN0 + i,
				 mask, enable ? mask : 0);
		if (ret && !err)
			err = ret;
	}

	return err;
}

static int wcd934x_slim_port_clear(struct wcd934x_codec *wcd,
                                 struct wcd_slim_codec_dai_data *dai)
{
	u32 ports = (dai->sconfig.port_mask >> 16) |
		    (dai->sconfig.port_mask << 16);
	unsigned int mask, i;
	int ret, err = 0;

	for (i = 0; i < 4; i++) {
		mask = (ports >> (8 * i)) & 0xff;
		if (!mask)
			continue;
		ret = regmap_write(wcd->if_regmap,
				   WCD934X_SLIM_PGD_PORT_INT_CLR_RX_0 + i,
				   mask);
		if (ret && !err)
			err = ret;
	}

	return err;
}

'''
start = old.index('static int wcd934x_trigger(')
end = old.index('static int wcd934x_set_channel_map(', start)
trigger = '''static int wcd934x_trigger(struct snd_pcm_substream *substream, int cmd,
                          struct snd_soc_dai *dai)
{
	struct wcd934x_codec *wcd = snd_soc_component_get_drvdata(dai->component);
	struct wcd_slim_codec_dai_data *dai_data = &wcd->dai[dai->id];
	int ret = 0, cleanup;

	switch (cmd) {
	case SNDRV_PCM_TRIGGER_START:
	case SNDRV_PCM_TRIGGER_RESUME:
	case SNDRV_PCM_TRIGGER_PAUSE_RELEASE:
		ret = wcd934x_slim_port_interrupts(wcd, dai_data, false);
		if (ret)
			break;
		ret = wcd934x_slim_port_clear(wcd, dai_data);
		if (ret)
			break;
		ret = slim_stream_prepare(dai_data->sruntime, &dai_data->sconfig);
		if (ret)
			break;
		ret = slim_stream_enable(dai_data->sruntime);
		if (ret) {
			slim_stream_unprepare(dai_data->sruntime);
			wcd934x_slim_port_clear(wcd, dai_data);
			break;
		}
		ret = wcd934x_slim_port_interrupts(wcd, dai_data, true);
		if (ret) {
			wcd934x_slim_port_interrupts(wcd, dai_data, false);
			slim_stream_disable(dai_data->sruntime);
			slim_stream_unprepare(dai_data->sruntime);
			wcd934x_slim_port_clear(wcd, dai_data);
		}
		break;
	case SNDRV_PCM_TRIGGER_STOP:
	case SNDRV_PCM_TRIGGER_SUSPEND:
	case SNDRV_PCM_TRIGGER_PAUSE_PUSH:
		/* Mask FIFO/port-closed events before disconnecting the bus. */
		ret = wcd934x_slim_port_interrupts(wcd, dai_data, false);
		cleanup = slim_stream_disable(dai_data->sruntime);
		if (!ret)
			ret = cleanup;
		cleanup = slim_stream_unprepare(dai_data->sruntime);
		if (!ret)
			ret = cleanup;
		cleanup = wcd934x_slim_port_clear(wcd, dai_data);
		if (!ret)
			ret = cleanup;
		break;
	default:
		return -EINVAL;
	}
	if (of_machine_is_compatible("realme,samurai"))
		dev_info(dai->dev, "samurai slim trigger dai=%d command=%d channels=%u rate=%u ret=%d\\n",
			 dai->id, cmd, dai_data->sconfig.ch_count,
			 dai_data->sconfig.rate, ret);
	return ret;
}

'''
s = old[:start] + helpers + trigger + old[end:]
start = s.index('static void wcd934x_codec_enable_int_port(')
end = s.index('static void wcd934x_codec_hd2_control(', start)
s = s[:start] + s[end:]
import re
s, count = re.subn(r'SND_SOC_DAPM_AIF_(IN|OUT)_E\(("AIF[1-4] (?:PB|CAP)"), ("AIF[1-4] (?:Playback|Capture)"), 0, SND_SOC_NOPM,\n\s+(AIF[1-4]_(?:PB|CAP)), 0, wcd934x_codec_enable_slim,\n\s+SND_SOC_DAPM_POST_PMU \| SND_SOC_DAPM_POST_PMD\)',
                  r'SND_SOC_DAPM_AIF_\1(\2, \3, 0, SND_SOC_NOPM,\n\t\t\t    \4, 0)', s)
assert count == 7
start = s.index('static irqreturn_t wcd934x_slim_irq_handler(')
end = s.index('\nstatic ', start + 1)
irq = s[start:end]
irq = irq.replace('regmap_read(wcd->if_regmap, i, &val);', 'if (regmap_read(wcd->if_regmap, i, &val))\n\t\t\treturn IRQ_NONE;')
irq = irq.replace('regmap_read(wcd->if_regmap,\n\t\t\t    WCD934X_SLIM_PGD_PORT_INT_RX_SOURCE0 + j, &val);',
                  'if (regmap_read(wcd->if_regmap,\n\t\t\t\tWCD934X_SLIM_PGD_PORT_INT_RX_SOURCE0 + j, &val))\n\t\t\tcontinue;')
irq = irq.replace('regmap_read(wcd->if_regmap, reg, &int_val);',
                  'if (regmap_read(wcd->if_regmap, reg, &int_val))\n\t\t\t\tcontinue;\n\t\t\tif (!(int_val & BIT(port_id % 8)))\n\t\t\t\tgoto clear;')
block_start = irq.index('\t\t\tregmap_read(\n')
block_end = irq.index('\n\t\t}', block_start)
irq = irq[:block_start] + '''			regmap_update_bits(wcd->if_regmap, reg,
					   BIT(port_id % 8), 0);''' + irq[block_end:]
irq = irq.replace('\n\t\tregmap_write(wcd->if_regmap,\n', '\n+clear:\n\t\tregmap_write(wcd->if_regmap,\n'.replace('\n+clear','\nclear'))
assert 'goto clear;' in irq and 'if (regmap_read' in irq
s = s[:start] + irq + s[end:]
p.write_text(s)
patch = 'Subject: [PATCH] ASoC: wcd934x: tie SLIM port interrupts to stream state\n\nMask selected port interrupts before disconnect, clear stale port events,\nand rearm after start, resume and pause release. Keep unrelated ports\nuntouched and propagate register setup errors. Acknowledge masked pending\nevents without reporting stopped ports as active FIFO errors.\n\n---\n'
patch += ''.join(difflib.unified_diff(old.splitlines(True), s.splitlines(True), fromfile='a/'+name, tofile='b/'+name))
(ref / 'wcd-port-lifecycle.patch').write_text(patch)
report = dict(stage=174, baseline_kernel=172, modified_this_stage=[name],
              before_sha256=baseline['source_sha256'], source_sha256={n:sha(k/n) for n in baseline['source_sha256']},
              dtb_and_ucm173_unchanged=True, build_and_runtime_pending=True)
for folder in [ref,out]:
    (folder/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K174_SOURCE_PREPARED',flush=True)
