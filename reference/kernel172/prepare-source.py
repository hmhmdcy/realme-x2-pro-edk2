from pathlib import Path
import hashlib, json, os, shutil, subprocess

os.umask(0o077)
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
assert not out.exists()
baseline = json.loads((ref.parent / 'kernel171/source-current-validation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, digest in baseline['source_sha256'].items():
    assert sha(k / name) == digest, name
assert set(subprocess.check_output(['git', 'diff', '--name-only'], cwd=k, text=True).splitlines()) == set(baseline['tracked_modified_files'])
out.mkdir(mode=0o700)
names = ['sound/soc/qcom/samurai-audio.c', 'sound/soc/codecs/wcd934x.c', 'sound/soc/codecs/wcd-mbhc-v2.c',
         'arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
for name in names:
    p = out / 'before-private' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(k / name, p)
shutil.copyfile(k / '.config', out / 'config-before-private')
shutil.copyfile(k / 'arch/arm64/boot/Image', out / 'Image-before168-private')
shutil.copyfile(k / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', out / 'dtb-before171-private')

machine = (k / names[0]).read_text()
machine = machine.replace('#include <linux/module.h>', '#include <linux/input.h>\n#include <linux/module.h>')
machine = machine.replace('#include <sound/pcm_params.h>', '#include <sound/jack.h>\n#include <sound/pcm_params.h>')
needle = 'static int samurai_fixup('
definition = '''struct samurai_audio_data {
	struct snd_soc_jack jack;
	struct snd_soc_component *jack_component;
	bool jack_created;
};

static struct snd_soc_jack_pin samurai_jack_pins[] = {
	{ .pin = "Headphone Jack", .mask = SND_JACK_HEADPHONE },
	{ .pin = "Mic Jack", .mask = SND_JACK_MICROPHONE },
	{ .pin = "Left Speaker", .mask = SND_JACK_HEADPHONE, .invert = 1 },
	{ .pin = "Right Speaker", .mask = SND_JACK_HEADPHONE, .invert = 1 },
};

static int samurai_setup_jack(struct snd_soc_pcm_runtime *rtd)
{
	static const unsigned int buttons[] = {
		SND_JACK_BTN_0, SND_JACK_BTN_1, SND_JACK_BTN_2, SND_JACK_BTN_3,
	};
	static const unsigned int keys[] = {
		KEY_PLAYPAUSE, KEY_VOICECOMMAND, KEY_VOLUMEUP, KEY_VOLUMEDOWN,
	};
	struct samurai_audio_data *data = snd_soc_card_get_drvdata(rtd->card);
	struct snd_soc_dai *codec;
	int i, ret;

	if (!data->jack_created) {
		ret = snd_soc_card_jack_new_pins(rtd->card, "Headset Jack",
				SND_JACK_HEADSET | SND_JACK_BTN_0 | SND_JACK_BTN_1 |
				SND_JACK_BTN_2 | SND_JACK_BTN_3,
				&data->jack, samurai_jack_pins,
				ARRAY_SIZE(samurai_jack_pins));
		if (ret)
			return ret;
		ret = snd_jack_add_new_kctl(data->jack.jack, "Headset Mic Jack",
					  SND_JACK_MICROPHONE);
		if (ret)
			return ret;
		for (i = 0; i < ARRAY_SIZE(buttons); i++) {
			ret = snd_jack_set_key(data->jack.jack, buttons[i], keys[i]);
			if (ret)
				return ret;
		}
		data->jack_created = true;
	}

	for_each_rtd_codec_dais(rtd, i, codec) {
		/* RX and TX share this WCD component, but keep both channel maps. */
		if (data->jack_component == codec->component)
			continue;
		if (data->jack_component)
			return -EINVAL;
		ret = snd_soc_dai_set_sysclk(codec, 0, 9600000,
					     SNDRV_PCM_STREAM_PLAYBACK);
		if (ret)
			return ret;
		ret = snd_soc_component_set_jack(codec->component, &data->jack, NULL);
		if (ret)
			return ret;
		data->jack_component = codec->component;
		dev_info(rtd->card->dev, "WCD934x headset detection connected\\n");
	}
	return 0;
}

'''
assert machine.count(needle) == 1
machine = machine.replace(needle, definition + needle)
old = '\t}\n\treturn 0;\n}\n\nstatic int samurai_startup'
assert machine.count(old) == 1
machine = machine.replace(old, '\t}\n\treturn samurai_setup_jack(rtd);\n}\n\nstatic int samurai_startup')
machine = machine.replace('struct snd_soc_card *card;\n\tstruct snd_soc_dai_link *link;',
                          'struct snd_soc_card *card;\n\tstruct samurai_audio_data *data;\n\tstruct snd_soc_dai_link *link;')
machine = machine.replace('\tcard->owner = THIS_MODULE;\n', '''	card->owner = THIS_MODULE;
	data = devm_kzalloc(&pdev->dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;
	snd_soc_card_set_drvdata(card, data);
''')
(k / names[0]).write_text(machine)

codec = (k / names[1]).read_text()
assert codec.count('\tbool mbhc_started;') == 1
codec = codec.replace('\tbool mbhc_started;', '\tbool mbhc_started;\n\tstruct snd_soc_jack *mbhc_jack;')
old = '\tret = wcd_dt_parse_micbias_info(&wcd->common);\n\tif (ret)\n\t\treturn ret;\n'
assert codec.count(old) == 1
codec = codec.replace(old, old + '\n\twcd->mbhc_cfg.micb_mv = wcd->common.micb_mv[MIC_BIAS_2 - 1];\n')
codec = codec.replace('\tcfg->micb_mv = wcd->common.micb_mv[1];\n', '')
old = '''	if (IS_ERR(wcd->mbhc)) {
		wcd->mbhc = NULL;
		return -EINVAL;
	}'''
new = '''	if (IS_ERR(wcd->mbhc)) {
		int ret = PTR_ERR(wcd->mbhc);

		wcd->mbhc = NULL;
		return ret;
	}'''
assert codec.count(old) == 1
codec = codec.replace(old, new)
old = '''	if (wcd934x_mbhc_init(component))
		dev_err(component->dev, "Failed to Initialize MBHC\\n");

	return 0;'''
new = '''	ret = wcd934x_mbhc_init(component);
	if (ret) {
		wcd_clsh_ctrl_free(wcd->clsh_ctrl);
		return dev_err_probe(component->dev, ret, "Failed to initialize MBHC\\n");
	}

	return 0;'''
assert codec.count(old) == 1
codec = codec.replace(old, new)
old = '\twcd_mbhc_deinit(wcd->mbhc);\n}'
new = '''	wcd_mbhc_deinit(wcd->mbhc);
	wcd->mbhc = NULL;
	wcd->mbhc_started = false;
	wcd->mbhc_jack = NULL;
}'''
assert codec.count(old) == 1
codec = codec.replace(old, new)
old = '''	if (jack && !wcd->mbhc_started) {
		ret = wcd_mbhc_start(wcd->mbhc, &wcd->mbhc_cfg, jack);
		wcd->mbhc_started = true;
	} else if (wcd->mbhc_started) {
		wcd_mbhc_stop(wcd->mbhc);
		wcd->mbhc_started = false;
	}'''
new = '''	if (jack) {
		if (wcd->mbhc_started)
			return wcd->mbhc_jack == jack ? 0 : -EBUSY;
		ret = wcd_mbhc_start(wcd->mbhc, &wcd->mbhc_cfg, jack);
		if (ret)
			return ret;
		wcd->mbhc_jack = jack;
		wcd->mbhc_started = true;
		if (of_machine_is_compatible("realme,samurai"))
			dev_info(comp->dev, "samurai MBHC started: micbias=%u mV\\n",
				 wcd->mbhc_cfg.micb_mv);
	} else if (wcd->mbhc_started) {
		wcd_mbhc_stop(wcd->mbhc);
		wcd->mbhc_started = false;
		wcd->mbhc_jack = NULL;
	}'''
assert codec.count(old) == 1
codec = codec.replace(old, new)
(k / names[1]).write_text(codec)

mbhc = (k / names[2]).read_text()
old = '\tif (!mbhc || !cfg || !jack)\n\t\treturn -EINVAL;'
new = old + '''
	/* ADC threshold scaling uses this voltage as a divisor. */
	if ((cfg->hs_thr || cfg->hph_thr) && !cfg->micb_mv)
		return -EINVAL;'''
assert mbhc.count(old) == 1
mbhc = mbhc.replace(old, new)
assert mbhc.count('cfg->btn_high[i] = 500000;') == 1
mbhc = mbhc.replace('cfg->btn_high[i] = 500000;', 'cfg->btn_high[i] = 500;')
(k / names[2]).write_text(mbhc)

dts = (k / names[3]).read_text()
old = '"Microphone", "Secondary Mic", "Microphone", "Speaker Mic";'
new = '"Microphone", "Secondary Mic", "Microphone", "Speaker Mic",\n\t\t\t  "Microphone", "Mic Jack";'
assert dts.count(old) == 1
dts = dts.replace(old, new)
old = '\t\t\t\t"Headphone Jack", "HPHL", "Headphone Jack", "HPHR",\n'
new = old + '\t\t\t\t"AMIC2", "Mic Jack", "AMIC2", "MIC BIAS2", "AMIC2", "MCLK",\n'
assert dts.count(old) == 1
dts = dts.replace(old, new)
(k / names[3]).write_text(dts)
subprocess.run(['git', 'diff', '--check'], cwd=k, check=True)
report = dict(stage=172, baseline_kernel=168, baseline_dtb=171, modified_this_stage=names,
              before_sha256={name:sha(out/'before-private'/name) for name in names},
              after_sha256={name:sha(k/name) for name in names},
              sd1_preserved=True, gain_and_protection_configuration_not_modified=True,
              no_physical_headset_test_performed=True, build_and_runtime_pending=True)
for directory in [ref, out]:
    (directory/'source-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
