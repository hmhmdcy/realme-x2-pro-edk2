"""Finish current-context invalidation and log captured CCM provenance."""
from pathlib import Path
import shutil
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
name='src/ipa/camss-vfe/camss.cpp';p=tree/name;s=p.read_text()
a=''' if (result.parametersKnown && context==std::prev(parameterHistory_.end()) && result.sensorControlsKnown) {
  ccmInputs_=ColourCorrectionInputs{ result.luxValid ? std::optional<float>(result.luxIndex) : std::nullopt,
                                   float(helper_->gain(sensorContext.gainCode)),sof };
 }'''
b=''' if (result.parametersKnown && context==std::prev(parameterHistory_.end())) {
  ccmInputs_.reset();
  if (result.sensorControlsKnown)
   ccmInputs_=ColourCorrectionInputs{ result.luxValid ? std::optional<float>(result.luxIndex) : std::nullopt,
                                    float(helper_->gain(sensorContext.gainCode)),sof };
 }'''
assert a in s;s=s.replace(a,b)
a='\twhile (parameterHistory_.size() > 64) parameterHistory_.erase(parameterHistory_.begin());'
b=''' const auto &ccm=parameterHistory_.at(firstSof).colourCorrection;
 if (ccm && ccm->aecValue) {
  LOG(IPACamss,Info)<<"CCM_APPLIED epoch="<<epoch<<" revision="<<revision<<" first-sof="<<firstSof
   <<" statistics-sof="<<ccm->statisticsSof.value_or(firstSof)
   <<" aec-bits="<<std::bit_cast<uint32_t>(*ccm->aecValue)<<" kelvin="<<ccm->temperature.value_or(0);
 }
'''+a
assert a in s;s=s.replace(a,b);p.write_text(s);shutil.copyfile(p,HERE/'ipa/camss.cpp')
p=tree/'src/ipa/camss-vfe/colour_correction_profile.cpp';s=p.read_text().replace('''\t/* DRC, HDR and flash coordinates remain explicit references; the AEC
  * coordinate may come from the per-frame runtime observation. Other
\t * runtime AEC/DRC/flash inputs are available. CCT is selected per revision. */''',''' /* DRC, HDR and flash coordinates remain explicit references. The optional
  * runtime AEC coordinate and CCT are selected for each ISP revision. */''')
p.write_text(s);shutil.copyfile(p,HERE/'ipa'/p.name)
