from pathlib import Path
import json, shutil
import host, storage

HERE=Path(__file__).resolve().parent
new=storage.candidate();baselineRoot=new.parent/'libcamera342-r27-built'
assert not new.exists()
shutil.copytree(baselineRoot,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2'
for stage,names in [(346,['aec_exposure_table.cpp','aec_exposure_table.h']),(358,['aec_antibanding.cpp','aec_antibanding.h'])]:
    for name in names:shutil.copyfile(HERE.parent/f'kernel{stage}/libipa'/name,tree/'src/ipa/libipa'/name)
for name in ['hardware_agc.cpp','hardware_agc.h','exposure_program.cpp','exposure_program.h']:
    shutil.copyfile(HERE/'ipa'/name,tree/'src/ipa/camss-vfe'/name)
changed=[]
def edit(name,old,new):
    p=tree/name;s=p.read_text();assert old in s,(name,old);p.write_text(s.replace(old,new));changed.append(name)
edit('src/ipa/libipa/meson.build',"    'aec_lux.cpp',","    'aec_lux.cpp',\n    'aec_exposure_table.cpp',\n    'aec_antibanding.cpp',")
edit('src/ipa/camss-vfe/meson.build',"'dynamic_lens_shading.cpp']","'dynamic_lens_shading.cpp', 'exposure_program.cpp']")
edit('src/ipa/libipa/agc_mean_luminance.h','\tdouble effectiveYTarget() const;', '''	/* Return the filtered total exposure before the exposure-mode allocator.
	 * Custom allocators use this same target and convergence policy. */
	utils::Duration calculateNewExposureValue(uint32_t constraintModeIndex,
					const Histogram &yHist, utils::Duration effectiveExposureValue);

	double effectiveYTarget() const;''')
p=tree/'src/ipa/libipa/agc_mean_luminance.cpp';s=p.read_text();start=s.index('std::tuple<utils::Duration, double, double, double>\nAgcMeanLuminance::calculateNewEv');end=s.index('\n/**',start+10)
old=s[start:end];body=old[old.index('\tif (effectiveExposureValue == 0s)'):]
body=body.replace('return exposureModeHelper->splitExposure(10ms);','return 10ms;').replace('return exposureModeHelper->splitExposure(newExposureValue);','return newExposureValue;')
newbody='''std::tuple<utils::Duration, double, double, double>
AgcMeanLuminance::calculateNewEv(uint32_t constraintModeIndex,
				 uint32_t exposureModeIndex, const Histogram &yHist,
				 utils::Duration effectiveExposureValue)
{
	auto helper = exposureModeHelpers_.at(exposureModeIndex);
	return helper->splitExposure(calculateNewExposureValue(constraintModeIndex, yHist,
							  effectiveExposureValue));
}

utils::Duration AgcMeanLuminance::calculateNewExposureValue(uint32_t constraintModeIndex,
							const Histogram &yHist,
							utils::Duration effectiveExposureValue)
{
'''+body
p.write_text(s[:start]+newbody+s[end:]);changed.append(str(p.relative_to(tree)))
(HERE/'source-state.json').write_text(json.dumps(dict(stage=359,source=str(tree),baseline=str(baselineRoot/'src/libcamera-v0.7.2'),
    baseline_installed_package_stage=342,changed=sorted(set(changed)),installed=False),indent=2)+'\n')
print('Prepared E-drive candidate from342 and separated filtered AE target from allocation.')
