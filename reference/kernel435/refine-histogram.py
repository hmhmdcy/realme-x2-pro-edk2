"""Retain the histogram selected by the native TMC trigger policy."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';D=T/'src/ipa/camss-vfe'
def edit(p,a,b):
 t=p.read_text();assert t.count(a)==1,(str(p),a,t.count(a));p.write_text(t.replace(a,b))
edit(D/'ipe_tone_profile.h','uint64_t gtmCookie = 0, gtmGeneration = 0;','uint64_t gtmCookie = 0, gtmGeneration = 0;\n bool tmcHistogramValid = false;\n uint32_t tmcHistogramSof = 0;\n std::array<uint32_t,1024> tmcHistogram{};')
edit(D/'ipe_tone_profile.cpp','history.policy.moduleEnable, 1, 0, 0, 1, 0, history.policy.cachedTriggers,','history.policy.moduleEnable, 1, 0, 0, 1, uint32_t(gtmConfigured_ && history.tmcHistogramValid), history.policy.cachedTriggers,')
edit(D/'ipe_tone_profile.cpp','''if (!generateTmc11Curve(r, 1, 1, tmcGamma_, logWeights_, &frame.histogram, &adrc)) return -ERANGE;''','''const std::array<uint32_t,1024> *histogram=&frame.histogram;
   if(gtmConfigured_) {
    if(state.policy.histogramSource==2) {state.tmcHistogram=frame.histogram;state.tmcHistogramSof=frame.sof;state.tmcHistogramValid=true;}
    histogram=state.policy.histogramSource && state.tmcHistogramValid?&state.tmcHistogram:nullptr;
   }
   if (!generateTmc11Curve(r, 1, 1, tmcGamma_, logWeights_, histogram, &adrc)) return -ERANGE;''')
edit(D/'ipe_tone_profile.cpp','''state.policy=appliedTmc->policy;state.adrc=appliedTmc->adrc;state.cache=appliedTmc->cache;''','''state.policy=appliedTmc->policy;state.adrc=appliedTmc->adrc;state.cache=appliedTmc->cache;
   state.tmcHistogramValid=appliedTmc->tmcHistogramValid;state.tmcHistogram=appliedTmc->tmcHistogram;state.tmcHistogramSof=appliedTmc->tmcHistogramSof;''')
state=json.loads((HERE/'source-state.json').read_text())
for r in state['source_hashes']:r['sha256']=hashlib.sha256((T/r['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
