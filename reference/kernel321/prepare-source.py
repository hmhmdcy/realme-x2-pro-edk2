"""Build an isolated LSC IPA from the actually deployed r25 source."""
from pathlib import Path
import json,shutil,hashlib
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
OLD=SDK/'work/libcamera316-r25-built';NEW=SDK/'work/libcamera321-lsc-built'
SRC='src/libcamera-v0.7.2'
assert not NEW.exists()
shutil.copytree(OLD,NEW,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before')])
for name in ['camss.cpp','parameter_encoder.h','parameter_encoder.cpp','params.h','meson.build']:
 p=HERE/'ipa'/name;assert not p.exists();shutil.copyfile(OLD/SRC/'src/ipa/camss-vfe'/name,p)
lib=HERE/'libipa';lib.mkdir()
for name in ['lens_shading.h','lens_shading.cpp']:
 shutil.copyfile(HERE.parent/'kernel317/libipa'/name,lib/name)
for name in ['lsc_resample.h','lsc_resample.cpp']:
 s=(HERE.parent/'kernel319/libipa'/name).read_text().replace('../../kernel317/libipa/lens_shading.h','lens_shading.h')
 (lib/name).write_text(s)
p=HERE/'ipa/params.h';s=p.read_text().replace('\tAecBhist,','\tAecBhist,\n\tLensShading,').replace('CAMSS_DEFINE_BLOCK_TYPE(AecBhist, aec_bhist, AEC_BHIST);','CAMSS_DEFINE_BLOCK_TYPE(AecBhist, aec_bhist, AEC_BHIST);\nCAMSS_DEFINE_BLOCK_TYPE(LensShading, lsc, LSC);');p.write_text(s)
p=HERE/'ipa/parameter_encoder.h';s=p.read_text().replace('#include <cstdint>','#include <cstdint>\n#include <linux/qcom-camss-config.h>')
s=s.replace('const Rectangle &roi, size_t *bytesused);','const Rectangle &roi, size_t *bytesused,\n\t\t     const camss_params_lsc *lsc = nullptr);');p.write_text(s)
p=HERE/'ipa/parameter_encoder.cpp';s=p.read_text().replace('#include <cmath>','#include <cmath>\n#include <cstring>')
s=s.replace('const Rectangle &roi, size_t *bytesused)','const Rectangle &roi, size_t *bytesused,\n\t\t     const camss_params_lsc *lsc)')
s=s.replace('constexpr size_t required =','const size_t required =').replace('sizeof(camss_params_aec_bhist);','sizeof(camss_params_aec_bhist) + (lsc ? sizeof(*lsc) : 0);')
s=s.replace('\t*bytesused = params.bytesused();','''
 if (lsc) {
  auto block = params.block<CamssBlocks::LensShading>();
  block.setEnabled(true);
  std::memcpy(&block->cell_width, &lsc->cell_width, sizeof(*lsc) - sizeof(lsc->header));
 }
\t*bytesused = params.bytesused();''');p.write_text(s)
p=HERE/'ipa/camss.cpp';s=p.read_text().replace('#include "parameter_encoder.h"','#include "parameter_encoder.h"\n#include "lens_shading.h"')
s=s.replace('\tResidualBlackProfile profile_', '\tstd::optional<camss_params_lsc> lensShading_;\n\tResidualBlackProfile profile_')
s=s.replace(' profile_ = { 0, 1.0 };',' profile_ = { 0, 1.0 }; lensShading_.reset();')
s=s.replace('  const ValueNode &tuning=*selected;','  const ValueNode &tuning=*selected;\n  ret=configureLensShading(tuning["lens_shading"],input,&lensShading_);\n  if (ret) return ret;')
s=s.replace('sizeof(camss_params_aec_bhist)> packet;','sizeof(camss_params_aec_bhist) + sizeof(camss_params_lsc)> packet;')
s=s.replace('input_, Rectangle(input_), &used);','input_, Rectangle(input_), &used, lensShading_ ? &*lensShading_ : nullptr);',1)
needle='ret = encodeParameters(it->second.memory->planes()[0], profile_, red, blue, input_, Rectangle(input_), &used);'
assert needle in s;s=s.replace(needle,needle.replace('&used);','&used, revision==0 && lensShading_ ? &*lensShading_ : nullptr);'))
s=s.replace('  << " delayed-controls=" << sensorConfiguration->enabled;','  << " delayed-controls=" << sensorConfiguration->enabled << " lsc=" << bool(lensShading_);')
p.write_text(s)
p=HERE/'ipa/meson.build';s=p.read_text().replace("'hardware_awb.cpp']","'hardware_awb.cpp', 'lens_shading.cpp']");p.write_text(s)
target=NEW/SRC/'src/ipa/libipa/meson.build';s=target.read_text();at=s.index("    'camera_sensor_helper.cpp',")
s=s[:at]+"    'lens_shading.cpp',\n    'lsc_resample.cpp',\n"+s[at:];target.write_text(s)
shutil.copyfile(target,lib/'meson.build')
for folder,dest in [('ipa','src/ipa/camss-vfe'),('libipa','src/ipa/libipa')]:
 for p in (HERE/folder).iterdir():shutil.copyfile(p,NEW/SRC/dest/p.name)
shutil.copyfile(HERE.parent/'kernel318/kernel/qcom-camss-config.h',NEW/SRC/'include/linux/qcom-camss-config.h')
report=dict(stage=321,source=str(NEW/SRC),baseline=str(OLD/SRC),baseline_ipa_sha256=hashlib.sha256((OLD/SRC/'src/ipa/camss-vfe/camss.cpp').read_bytes()).hexdigest(),installed=False)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
