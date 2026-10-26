"""Replace the obsolete lab power dependency with standard sensor resources."""
from pathlib import Path
import difflib,hashlib,json,re,subprocess

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel270')
U=Path('/home/cy122/x2pro-linux/upstream')
W=Path('/home/cy122/x2pro-linux/camera270-kernel')
base='1f5da50bbcba4fbe89917db7987429fdf078f257'
G=['git','-c','safe.directory='+str(U),'-C',str(U)]
assert subprocess.check_output(G+['rev-parse','HEAD'],text=True).strip()==base
assert not subprocess.check_output(G+['status','--porcelain'],text=True).strip()
assert not W.exists()
text=(R.parent/'kernel240/s5k3m5.c').read_text()
expected=json.loads((R.parent/'kernel240/s5k3m5-source-validation.json').read_text())
assert hashlib.sha256(text.encode()).hexdigest()==expected['source_sha256']
header=(R.parent/'kernel240/s5k3m5-oem-tables.h').read_text()
assert hashlib.sha256(header.encode()).hexdigest()==expected['header_sha256']

# Keep the independently decoded register sequences and reviewed PM/stream fixes.
# Remove all lab supplier discovery and all voltage programming from the sensor.
start=text.index('static int s5k3m5_match_lab_child(')
end=text.index('static int s5k3m5_rmx_power_off(',start)
text=text[:start]+'''static int s5k3m5_clock19_resources(struct s5k3m5 *sensor)
{
	struct device *dev = sensor->dev;
	unsigned int i;

	sensor->reset_gpio = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(sensor->reset_gpio))
		return PTR_ERR(sensor->reset_gpio);

	/* AF is an independent actuator; only the sensor's three rails belong here. */
	for (i = 1; i < S5K3M5_NUM_SUPPLIES; i++) {
		sensor->supplies[i].supply = s5k3m5_supply_names[i];
		sensor->supplies[i].consumer =
			devm_regulator_get(dev, s5k3m5_supply_names[i]);
		if (IS_ERR(sensor->supplies[i].consumer))
			return PTR_ERR(sensor->supplies[i].consumer);
	}

	return 0;
}

'''+text[end:]
text=text.replace('#include <linux/platform_device.h>\n','').replace('#include <linux/string.h>\n','')
text=text.replace('/* RMX1931: PM callbacks are serialized by runtime PM, never take state_lock. */',
 '/* Runtime PM serializes the sensor power callbacks. */')
text=text.replace('s5k3m5_rmx_resources','s5k3m5_clock19_resources')
text=text.replace('RMX1931 power resources unavailable','sensor power resources unavailable')
text=text.replace('bool rmx1931;','bool clock19_sequence;')
text=text.replace('->rmx1931','->clock19_sequence').replace('.rmx1931 = true','.clock19_sequence = true')
for name in ['modes','link_freqs','profile','init','mode3_regs','power_on','power_off','cleanup']:
 text=text.replace('s5k3m5_rmx_'+name,'s5k3m5_clock19_'+name)
header=header.replace('s5k3m5_rmx_init','s5k3m5_clock19_init').replace('s5k3m5_rmx_mode3_regs','s5k3m5_clock19_mode3_regs')
text=text.replace('s5k3m5-oem-tables.h','s5k3m5-19mhz-tables.h')
old='''	s5k3m5->profile = device_get_match_data(&client->dev);
	if (!s5k3m5->profile)
		s5k3m5->profile = &s5k3m5_default_profile;
'''
assert text.count(old)==1;text=text.replace(old,'')
old='''	freq = clk_get_rate(s5k3m5->mclk);
	if (freq != s5k3m5->profile->mclk_rate)'''
new='''	freq = clk_get_rate(s5k3m5->mclk);
	switch (freq) {
	case 19200000:
		s5k3m5->profile = &s5k3m5_clock19_profile;
		break;
	case S5K3M5_MCLK_FREQ_24MHZ:
		s5k3m5->profile = &s5k3m5_default_profile;
		break;
	default:
		return dev_err_probe(s5k3m5->dev, -EINVAL,
				     "unsupported MCLK frequency %lu\\n", freq);
	}
	if (freq != s5k3m5->profile->mclk_rate)'''
assert text.count(old)==1;text=text.replace(old,new)
old='''	{ .compatible = "realme,rmx1931-s5k3m5", .data = &s5k3m5_clock19_profile },
	{ .compatible = "samsung,s5k3m5", .data = &s5k3m5_default_profile },'''
assert text.count(old)==1;text=text.replace(old,'\t{ .compatible = "samsung,s5k3m5" },')
text=text.replace('\tbool lease_busy;\n','')
old='''	/* A first-P-output lease conflict is retryable after our own rollback. */
	lease_busy = ret == -EBUSY && !sensor->supply_enabled[1] && !sensor->supply_enabled[2];
	if (!lease_busy)
		sensor->power_fault = true;
'''
assert text.count(old)==1;text=text.replace(old,'\t/* A clean rollback permits a later retry through runtime PM. */\n')
text=text.replace('before power/lease release','before removing sensor power')
text=text.replace('managed cleanup incomplete, P fault remains latched','managed sensor power cleanup incomplete')
assert not any(s in text for s in ['of_machine_is_compatible','pm8008-reg-lab','pm8008-imx319-lab','device_find_child','regulator_set_voltage','realme,rmx1931','lease_busy'])

subprocess.run(G+['worktree','add','-b','samurai-multicamera270',str(W),base],check=True,capture_output=True)
target=W/'drivers/media/i2c/s5k3m5.c';original=target.read_text()
target.write_text(text)
(W/'drivers/media/i2c/s5k3m5-19mhz-tables.h').write_text(header)
(R/'s5k3m5.c').write_text(text)
(R/'s5k3m5-19mhz-tables.h').write_text(header)
(R/'s5k3m5-standard-resources.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/i2c/s5k3m5.c',tofile='b/drivers/media/i2c/s5k3m5.c')))
report=dict(stage=270,base_commit=base,work_branch='samurai-multicamera270',
 source_sha256=hashlib.sha256(text.encode()).hexdigest(),header_sha256=hashlib.sha256(header.encode()).hexdigest(),
 standard_sensor_compatible=True,profile_selected_by_input_clock=True,no_lab_or_board_supplier_discovery=True,
 sensor_voltage_constraints_from_regulators=True,independently_decoded_917_init_and53_mode_records_preserved=True,
 existing_24mhz_profile_retained=True,link_frequency_723200000_unmeasured=True,
 initial_mode='2104x1560',compiled=False,phone_changed=False)
(R/'telephoto-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
