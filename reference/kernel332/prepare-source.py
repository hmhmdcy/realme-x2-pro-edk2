"""Extend the isolated330 candidate with optional calibrated inverse CCT."""
from pathlib import Path
import json,shutil
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
OLD=SDK/'work/libcamera330-wb-built';NEW=SDK/'work/libcamera332-cct-built';SRC='src/libcamera-v0.7.2'
assert not NEW.exists()
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
tree=NEW/SRC
def change(s,a,b):
 assert a in s,a
 return s.replace(a,b)
for name in ['awb_colour_temperature.cpp','awb_colour_temperature.h']:
 (HERE/'libipa').mkdir(exist_ok=True)
 shutil.copyfile(HERE.parent/'kernel331/libipa'/name,tree/'src/ipa/libipa'/name)
 shutil.copyfile(HERE.parent/'kernel331/libipa'/name,HERE/'libipa'/name)
p=tree/'src/ipa/libipa/meson.build';s=change(p.read_text(),"    'awb_calibration.cpp',","    'awb_calibration.cpp',\n    'awb_colour_temperature.cpp',");p.write_text(s)
(HERE/'ipa').mkdir(exist_ok=True)
p=tree/'src/ipa/camss-vfe/white_balance_reference.h';s=p.read_text()
s=change(s,'#include "../libipa/awb_calibration.h"','#include "../libipa/awb_calibration.h"\n#include "../libipa/awb_colour_temperature.h"')
s=change(s,'\tint gains(int32_t kelvin, double *red, double *blue) const;','\tint gains(int32_t kelvin, double *red, double *blue) const;\n\tstd::optional<int32_t> temperature(double red, double blue) const;')
s=change(s,'\tAwbIlluminantRatios ratios_;','\tAwbIlluminantRatios ratios_;\n\tstd::optional<AwbColourTemperatureModel> inverse_;');p.write_text(s)
p=tree/'src/ipa/camss-vfe/white_balance_reference.cpp';s=p.read_text()
needle='int WhiteBalanceReference::configure('
at=s.index(needle);s=s[:at]+'''std::optional<int32_t> WhiteBalanceReference::temperature(double red, double blue) const
{
	if (!inverse_ || !std::isfinite(red) || !std::isfinite(blue) || red <= 0 || blue <= 0)
		return std::nullopt;
	AwbColourTemperatureEstimate estimate;
	if (!inverse_->estimate({ float(1.0 / red), float(1.0 / blue) }, &estimate))
		return std::nullopt;
	return int32_t(std::lround(estimate.kelvin));
}

'''+s[at:]
needle='\t*reference = result;'
s=change(s,needle,'''\tconst auto &referencePoints = tuning["reference_points"];
	if (!referencePoints.isEmpty()) {
		AwbIlluminantRatios points, calibrated;
		if (!referencePoints.isList() || referencePoints.size() != points.size())
			return -EINVAL;
		for (unsigned int i = 0; i < points.size(); ++i)
			if (readRow(referencePoints[i], &points[i]))
				return -EINVAL;
		AwbColourTemperatureModel inverse;
		if (!awbCalibratedReferenceRatios(points, factors, &calibrated) || !inverse.configure(calibrated))
			return -EINVAL;
		result.inverse_ = inverse;
	}
'''+needle);p.write_text(s)
p=tree/'src/ipa/camss-vfe/camss.cpp';s=p.read_text()
s=change(s,'std::optional<int32_t> colourTemperature; };','std::optional<int32_t> colourTemperature, estimatedColourTemperature; };')
s=change(s,'if (context->second.colourTemperature) metadata->set(controls::ColourTemperature,*context->second.colourTemperature);',
 '''if (auto temperature = context->second.colourTemperature ? context->second.colourTemperature : context->second.estimatedColourTemperature)
  metadata->set(controls::ColourTemperature,*temperature);''')
s=change(s,'if (result.parametersKnown && context->second.colourTemperature) metadata.set(controls::ColourTemperature,*context->second.colourTemperature);',
 '''if (result.parametersKnown) {
  if (auto temperature = context->second.colourTemperature ? context->second.colourTemperature : context->second.estimatedColourTemperature)
   metadata.set(controls::ColourTemperature,*temperature);
 }''')
s=change(s,'red, blue, colourTemperature_ };','red, blue, colourTemperature_, whiteBalance_ ? whiteBalance_->temperature(effectiveRed,effectiveBlue) : std::nullopt };')
p.write_text(s)
names=['src/ipa/libipa/awb_colour_temperature.cpp','src/ipa/libipa/awb_colour_temperature.h','src/ipa/libipa/meson.build',
 'src/ipa/camss-vfe/white_balance_reference.cpp','src/ipa/camss-vfe/white_balance_reference.h','src/ipa/camss-vfe/camss.cpp']
for name in names:
 relative=Path('libipa' if '/libipa/' in name else 'ipa')/Path(name).name
 shutil.copyfile(tree/name,HERE/relative)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=332,source=str(tree),baseline=str(OLD/SRC),installed=False,default_profiles_changed=False,
 changed_sources=names,calibrated_inverse_cct_integrated=True,ccm_pending=True,kernel_and_board_changes=False),indent=2)+'\n')
print('Prepared optional reference-point CCT estimation in acknowledged parameter history.')
