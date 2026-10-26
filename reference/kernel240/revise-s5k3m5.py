"""Apply source-review fixes and independently verify OEM stream records."""
from pathlib import Path
import difflib
import hashlib
import json
import struct

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel240')
source=R/'s5k3m5.c';text=source.read_text()
backup=P/'sensor-before-review-private';assert not backup.exists();backup.mkdir(mode=0o700)
for name in ['s5k3m5.c','s5k3m5-power.c.inc','s5k3m5-source-validation.json']:
 (backup/name).write_bytes((R/name).read_bytes())
data=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.qtech_s5k3m5sx.bin').read_bytes()
entries={}
for pos in range(232,258784,72):
 ident=struct.unpack_from('<Q',data,pos)[0];name=data[pos+8:pos+40].split(b'\0')[0].decode();offset,size=struct.unpack_from('<QQ',data,pos+56)
 assert offset+size<=124424;entries[ident]=(name,258784+offset,size)
def qwords(ident,name):
 actual,start,size=entries[ident];assert actual==name and size%8==0
 return struct.unpack('<'+'Q'*(size//8),data[start:start+size])
streams=[]
for ident,addr,value,delay in [(692,0x100,1,0),(696,0x100,0,30000),(700,0x104,1,0),(704,0x104,0,0)]:
 row=qwords(ident,'regSetting');assert len(row)==10 and row[0]==row[7]==0 and row[2]==addr and row[3]==row[8]==1 and row[5]==2 and row[6]==1
 assert qwords(row[4],'registerData')==(value,) and qwords(row[9],'delayUs')==(delay,)
 streams.append(dict(register=addr,width_bits=8,value=value,delay_us=delay))
def replace(old,new):
 global text
 assert text.count(old)==1,(old[:100],text.count(old))
 text=text.replace(old,new)
replace('''	if (!pm_runtime_get_if_active(s5k3m5->dev))
		return 0;''','''	if (s5k3m5->profile->rmx1931 && (s5k3m5->removing || s5k3m5->power_fault))
		return -EIO;
	ret = pm_runtime_get_if_active(s5k3m5->dev);
	if (ret <= 0)
		return ret;''')
replace('''					     S5K3M5_EXPOSURE_MIN,''','''					     s5k3m5->profile->rmx1931 ? 1 : S5K3M5_EXPOSURE_MIN,''')
replace('__v4l2_ctrl_modify_range(s5k3m5->exposure, S5K3M5_EXPOSURE_MIN,',
 '__v4l2_ctrl_modify_range(s5k3m5->exposure, s5k3m5->profile->rmx1931 ? 1 : S5K3M5_EXPOSURE_MIN,')
replace('static int s5k3m5_enable_streams(','''static int s5k3m5_stop_hw(struct s5k3m5 *sensor)
{
	int ret;

	if (!sensor->profile->rmx1931)
		return cci_write(sensor->regmap, S5K3M5_REG_CTRL_MODE, 0, NULL);
	ret = cci_write(sensor->regmap, CCI_REG8(0x0100), 0, NULL);
	/* Actual OEM streamOffSettings: delayUs=30000 before power/lease release. */
	usleep_range(30000, 31000);
	return ret;
}

static int s5k3m5_enable_streams(''')
replace('''	cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE,
		  S5K3M5_MODE_STREAMING |
		  (s5k3m5->vflip->val ? S5K3M5_VFLIP : 0) |
		  (s5k3m5->hflip->val ? S5K3M5_HFLIP : 0), &ret);''','''	if (s5k3m5->profile->rmx1931) {
		cci_write(s5k3m5->regmap, CCI_REG8(0x0101),
			  (s5k3m5->vflip->val ? S5K3M5_VFLIP : 0) |
			  (s5k3m5->hflip->val ? S5K3M5_HFLIP : 0), &ret);
		cci_write(s5k3m5->regmap, CCI_REG8(0x0100), 1, &ret);
	} else {
		cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE,
			  S5K3M5_MODE_STREAMING |
			  (s5k3m5->vflip->val ? S5K3M5_VFLIP : 0) |
			  (s5k3m5->hflip->val ? S5K3M5_HFLIP : 0), &ret);
	}''')
replace('cleanup_ret = cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE, 0, NULL);','cleanup_ret = s5k3m5_stop_hw(s5k3m5);')
replace('ret = cci_write(s5k3m5->regmap, S5K3M5_REG_CTRL_MODE, 0, NULL);','ret = s5k3m5_stop_hw(s5k3m5);')
cleanup='''
static void s5k3m5_rmx_cleanup(void *data)
{
	struct s5k3m5 *sensor = data;
	int ret;

	if (!sensor->clock_enabled && !sensor->supply_enabled[1] &&
	    !sensor->supply_enabled[2] && !sensor->supply_enabled[3])
		return;
	ret = s5k3m5_rmx_power_off(sensor);
	if (ret)
		dev_err(sensor->dev, "managed cleanup incomplete, P fault remains latched: %d\\n", ret);
}
'''
power_path=R/'s5k3m5-power.c.inc';power=power_path.read_text()
assert text.count(power)==1
text=text.replace(power,power+cleanup)
power_path.write_text(power+cleanup)
replace('''			return dev_err_probe(s5k3m5->dev, ret, "RMX1931 power resources unavailable\\n");''','''			return dev_err_probe(s5k3m5->dev, ret, "RMX1931 power resources unavailable\\n");
		ret = devm_add_action_or_reset(s5k3m5->dev, s5k3m5_rmx_cleanup, s5k3m5);
		if (ret)
			return ret;''')
replace('''	pm_runtime_disable(s5k3m5->dev);
	pm_runtime_set_suspended(s5k3m5->dev);
subdev_cleanup_without_pm:''','''	pm_runtime_disable(s5k3m5->dev);
subdev_cleanup_without_pm:''')
replace('''power_off:
	s5k3m5_power_off(s5k3m5->dev);''','''power_off:
	{
		int cleanup_ret = s5k3m5_power_off(s5k3m5->dev);

		if (cleanup_ret)
			dev_err(s5k3m5->dev, "probe power cleanup incomplete: %d\\n", cleanup_ret);
		else
			pm_runtime_set_suspended(s5k3m5->dev);
	}''')
replace('''	if (!pm_runtime_status_suspended(s5k3m5->dev)) {
		s5k3m5_power_off(s5k3m5->dev);
		pm_runtime_set_suspended(s5k3m5->dev);
	}''','''	if (s5k3m5->profile->rmx1931 || !pm_runtime_status_suspended(s5k3m5->dev)) {
		int ret = s5k3m5_power_off(s5k3m5->dev);

		if (ret)
			dev_err(s5k3m5->dev, "remove power cleanup incomplete: %d\\n", ret);
		else
			pm_runtime_set_suspended(s5k3m5->dev);
	}''')
source.write_text(text)
base=(R/'s5k3m5-base.c').read_text()
(R/'s5k3m5-rmx1931.patch').write_text(''.join(difflib.unified_diff(base.splitlines(True),text.splitlines(True),fromfile='a/drivers/media/i2c/s5k3m5.c',tofile='b/drivers/media/i2c/s5k3m5.c')))
report=json.loads((R/'s5k3m5-source-validation.json').read_text())
report.update(source_sha256=hashlib.sha256(text.encode()).hexdigest(),
    power_include_sha256=hashlib.sha256(power_path.read_bytes()).hexdigest(),
    oem_stream_records_independently_decoded=streams,
    pm_control_negative_reference_result_checked=True,
    residual_rail_cleanup_independent_of_runtime_suspended_state=True,
    managed_probe_failure_cleanup_added=True,off_errors_not_reported_as_suspended=True,
    oem_stream_write8_and_off_delay30ms=True,oem_minimum_exposure_line=1,
    link_frequency_remains_unmeasured_op_pll_candidate=True,
    probe_lease_busy_requires_explicit_idle_reprobe=True)
(R/'s5k3m5-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=240,source_review_fixes_applied=True,source_sha256=report['source_sha256'],
    actual_oem_stream_off_delay_us=30000,no_phone_operation=True)))
