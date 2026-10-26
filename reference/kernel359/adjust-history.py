from pathlib import Path
import shutil
import storage

HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
for name in ['hardware_agc.cpp','hardware_agc.h','exposure_program.cpp','exposure_program.h']:
    shutil.copyfile(HERE/'ipa'/name,tree/'src/ipa/camss-vfe'/name)
def edit(name,old,new):
    p=tree/name;s=p.read_text();assert old in s,(name,old);p.write_text(s.replace(old,new))
cam='src/ipa/camss-vfe/camss.cpp'
edit(cam,'applyIspControls(uint64_t epoch, const ControlList &controls, AutoIspUpdate *update)',
 'applyIspControls(uint64_t epoch, uint32_t firstSof, const ControlList &controls, AutoIspUpdate *update)')
edit(cam,'ret=agc_->applyControls(controls);if(ret)return ret;}\n if (unchanged)',
 'ret=agc_->applyControls(controls,firstSof);if(ret)return ret;}\n if (unchanged)')
edit(cam,'agc_->metadata(metadata);','agc_->metadata(sof,metadata);')
edit(cam,'IPA_MODULE_API_VERSION, 0, "camss-vfe", "camss-vfe",','IPA_MODULE_API_VERSION, 1, "camss-vfe", "camss-vfe",')
edit('include/libcamera/ipa/camss.mojom','applyIspControls(uint64 epoch, libcamera.ControlList controls)',
 'applyIspControls(uint64 epoch, uint32 firstSof, libcamera.ControlList controls)')
pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
edit(pipeline,'createIPA<ipa::camss::IPAProxyCamss>(0, 0)','createIPA<ipa::camss::IPAProxyCamss>(1, 1)')
edit(pipeline,'ipa_->applyIspControls(epoch_, request.controls, &update)',
 'ipa_->applyIspControls(epoch_, uint32_t(int64_t(request.source) + *imageSequenceOffset_), request.controls, &update)')
print('Added effective SOF to algorithm-control application, historical metadata, and matched IPA pipeline version1.')
