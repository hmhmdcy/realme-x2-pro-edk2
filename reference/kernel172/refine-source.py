from pathlib import Path
import hashlib, json, subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel172')
report = json.loads((ref / 'source-validation.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name, digest in report['after_sha256'].items():
    assert sha(k / name) == digest, name
(out / 'source-validation-initial-private.json').write_text(json.dumps(report, indent=2) + '\n')

name = 'sound/soc/qcom/samurai-audio.c'
s = (k / name).read_text()
old = '\t{ .pin = "Mic Jack", .mask = SND_JACK_MICROPHONE },\n'
assert s.count(old) == 1
s = s.replace(old, old + '\t{ .pin = "Handset Mic", .mask = SND_JACK_MICROPHONE, .invert = 1 },\n')
old = '''		ret = snd_jack_add_new_kctl(data->jack.jack, "Headset Mic Jack",
					  SND_JACK_MICROPHONE);
		if (ret)
			return ret;
'''
assert s.count(old) == 1
s = s.replace(old, '')
(k / name).write_text(s)

name = 'sound/soc/codecs/wcd934x.c'
s = (k / name).read_text()
old = '''	snd_soc_add_component_controls(component, impedance_detect_controls,
				       ARRAY_SIZE(impedance_detect_controls));
	snd_soc_add_component_controls(component, hph_type_detect_controls,
				       ARRAY_SIZE(hph_type_detect_controls));

	return 0;
}'''
new = '''	ret = snd_soc_add_component_controls(component, impedance_detect_controls,
					     ARRAY_SIZE(impedance_detect_controls));
	if (!ret)
		ret = snd_soc_add_component_controls(component, hph_type_detect_controls,
						     ARRAY_SIZE(hph_type_detect_controls));
	if (ret) {
		wcd_mbhc_deinit(wcd->mbhc);
		wcd->mbhc = NULL;
	}

	return ret;
}'''
assert s.count(old) == 1
s = s.replace(old, new)
old = '\tstruct wcd_mbhc_intr *intr_ids = &wcd->intr_ids;\n'
assert s.count(old) == 1
s = s.replace(old, old + '\tint ret;\n')
s = s.replace('\t\tint ret = PTR_ERR(wcd->mbhc);', '\t\tret = PTR_ERR(wcd->mbhc);')
begin = s.index('static int wcd934x_init_dmic')
end = s.index('\nstatic int wcd934x_hw_init', begin)
part = s[begin:end]
for reg in ['WCD934X_ANA_MICB1', 'WCD934X_ANA_MICB2', 'WCD934X_ANA_MICB3', 'WCD934X_ANA_MICB4', 'WCD934X_TEST_DEBUG_PAD_DRVCTL_0']:
    prefix = '\tsnd_soc_component_update_bits(comp, ' + reg
    assert part.count(prefix) == 1
    a = part.index(prefix)
    b = part.index(';', a) + 1
    call = part[a:b]
    part = part[:a] + call.replace('\tsnd_soc_', '\tret = snd_soc_', 1) + '\n\tif (ret < 0)\n\t\treturn ret;' + part[b:]
s = s[:begin] + part + s[end:]
(k / name).write_text(s)
subprocess.run(['git', 'diff', '--check'], cwd=k, check=True)
report['after_sha256'] = {n: sha(k / n) for n in report['modified_this_stage']}
report['tracked_modified_files'] = subprocess.check_output(['git', 'diff', '--name-only'], cwd=k, text=True).splitlines()
report['source_sha256'] = {n: sha(k / n) for n in report['tracked_modified_files']}
report['jack_controls_use_asoc_pin_generated_controls'] = True
report['headset_capture_gates_internal_handset_mic_pin'] = True
report['micbias_register_and_mbhc_control_errors_propagated'] = True
for directory in [ref, out]:
    (directory / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report), flush=True)
