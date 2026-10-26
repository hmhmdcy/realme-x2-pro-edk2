"""Report standard AE policy on the normal statistics metadata path, too."""
from pathlib import Path
import shutil
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
shutil.copyfile(HERE/'ipa/hardware_agc.cpp',tree/'src/ipa/camss-vfe/hardware_agc.cpp')
p=tree/'src/ipa/camss-vfe/camss.cpp';s=p.read_text()
old=' if (lux_ && result.parametersKnown && result.sensorControlsKnown && result.rgbPresent) {'
new=' if (agc_ && result.parametersKnown && result.sensorControlsKnown) agc_->metadata(sof,&metadata);\n'+old
assert old in s;p.write_text(s.replace(old,new))
print('Added SOF-specific AE metadata to the normal statistics path; current policy avoids table rebuilds per frame.')
