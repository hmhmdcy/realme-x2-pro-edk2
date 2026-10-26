"""Apply frame-specific AE policy to delayed statistics and clamp initial SOF."""
from pathlib import Path
import shutil
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
for name in ['hardware_agc.cpp','hardware_agc.h']:
    shutil.copyfile(HERE/'ipa'/name,tree/'src/ipa/camss-vfe'/name)
p=tree/'src/ipa/camss-vfe/camss.cpp';s=p.read_text()
old='agc_->calculate(parsed.histogram, sensorContext.exposureLines, sensorContext.gainCode, &lines, &code)'
new='agc_->calculate(sof, parsed.histogram, sensorContext.exposureLines, sensorContext.gainCode, &lines, &code)'
assert old in s;p.write_text(s.replace(old,new))
p=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';s=p.read_text()
old='uint32_t(int64_t(request.source) + *imageSequenceOffset_)'
new='uint32_t(std::max<int64_t>(0, int64_t(request.source) + *imageSequenceOffset_))'
assert old in s;p.write_text(s.replace(old,new))
print('Delayed statistics now select their SOF policy; initial negative request offset clamps to zero.')
