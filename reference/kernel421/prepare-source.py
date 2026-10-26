"""Connect owned same-SOF observations to final aggregate frame completion."""
from pathlib import Path
import difflib,hashlib,json,re,shutil,sys
import host,storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();old=new.parent/'libcamera420-request-r31'
assert json.loads((HERE.parent/'kernel420/current-state-validation.json').read_text())['passed']
if new.exists():
 if sys.argv[1:]==['--refresh-source']:
  previous=json.loads((HERE/'source-state.json').read_text())
  for item in previous['source_hashes']:assert hashlib.sha256((new/'src/libcamera-v0.7.2'/item['path']).read_bytes()).hexdigest()==item['sha256']
 else:assert sys.argv[1:]==['--resume-preparation'] and not (HERE/'source-state.json').exists(),'Inspect existing candidate first'
else:shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';base=old/'src/libcamera-v0.7.2'
names=['include/libcamera/ipa/camss.mojom','src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/ipe_frame_history.h','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
p=tree/names[0];s=(base/names[0]).read_text();s=replace(s,'\tbool luxValid;','\tuint64 ipeToken;\n\tuint64 ipeHistogramTrace;\n\tuint64 exposureNs;\n\tfloat analogueGain;\n\tbool luxValid;')
s=replace(s,'\tstop();','\t[async] frameProcessed(uint64 epoch, uint32 sof, uint64 token, bool success);\n\tstop();');p.write_text(s)
p=tree/names[1];s=(base/names[1]).read_text();s=replace(s,'#include "statistics.h"','#include "statistics.h"\n#include "ipe_frame_history.h"')
s=replace(s,'\tvoid stop() override;','\tvoid frameProcessed(uint64_t epoch, uint32_t sof, uint64_t token, bool success) override;\n\tvoid stop() override;')
s=replace(s,'\tstd::optional<uint32_t> lastStats_;','\tIpeFrameHistory ipeHistory_;\n\tstd::optional<uint32_t> lastStats_;')
s=replace(s,'epoch_ = epoch;','if (!ipeHistory_.start(epoch)) return -EINVAL;\n epoch_ = epoch;')
s=replace(s,'\trunning_ = false;af_.cancel();initialAfTrigger_.reset();','\trunning_ = false;af_.cancel();initialAfTrigger_.reset();\n ipeHistory_.stop();\n const auto &count=ipeHistory_.counters();\n LOG(IPACamss,Info)<<"IPE_HISTORY_STOP epoch="<<epoch_<<" prepared="<<count.prepared<<" committed="<<count.committed\n  <<" discarded="<<count.discarded<<" superseded="<<count.superseded<<" aborted="<<count.aborted<<" pending="<<ipeHistory_.pendingCount();')
s=replace(s,'complete();\n}',(HERE/'ipa-observation-prepare.cpp').read_text()+' complete();\n}')
s=replace(s,'} /* namespace libcamera::ipa::camss */',(HERE/'ipa-observation-tail.cpp').read_text()+'\n} /* namespace libcamera::ipa::camss */')
s=replace(s,'IPA_MODULE_API_VERSION, 1, "camss-vfe", "camss-vfe"','IPA_MODULE_API_VERSION, 2, "camss-vfe", "camss-vfe"');p.write_text(s)
(tree/names[2]).write_bytes((HERE/'ipe_frame_history.h').read_bytes())
p=tree/names[3];s=(base/names[3]).read_text()
# Bump the private IPA interface version to reject mismatched module/proxy pairs.
line=next(l for l in s.splitlines() if 'createIPA<' in l);assert '(1, 1)' in line,line;s=s.replace(line,line.replace('(1, 1)','(2, 2)'))
s=replace(s,'bool imageFinished = false, rawReady = false, failed = false;','bool imageFinished = false, rawReady = false, failed = false;\n   uint64_t ipeToken = 0;\n   uint32_t ipeSof = 0;')
s=replace(s,'\t\tuint64_t weightedSum;','\t\tuint64_t weightedSum;\n\t\tuint64_t ipeToken, ipeTrace, exposureNs;\n\t\tfloat analogueGain;')
s=replace(s,'Histogram{ statistics.population, statistics.weightedSum, metadata }','Histogram{ statistics.population, statistics.weightedSum, statistics.ipeToken, statistics.ipeHistogramTrace, statistics.exposureNs, statistics.analogueGain, metadata }')
s=replace(s,'\t\trequest->_d()->metadata().merge(h.metadata);','\t\trequest->_d()->metadata().merge(h.metadata);\n  requests_.at(request).ipeToken=h.ipeToken;requests_.at(request).ipeSof=sequence;\n  if(h.ipeToken)LOG(CamssVfe,Info)<<"IPE_PAIR epoch="<<epoch_<<" sof="<<sequence<<" token="<<h.ipeToken\n   <<" trace="<<h.ipeTrace<<" exposure-ns="<<h.exposureNs<<" analogue-gain="<<h.analogueGain;')
s=replace(s,'histograms_.erase(histogramOrder_.front()); histogramOrder_.pop_front();','auto old=histograms_.find(histogramOrder_.front());\n   if(old!=histograms_.end() && old->second.ipeToken)ipa_->frameProcessed(epoch_,old->first,old->second.ipeToken,false);\n   histograms_.erase(histogramOrder_.front()); histogramOrder_.pop_front();')
# Erase request/ownership first. The asynchronous direct-module call may emit logs,
# and future algorithms must never retain a reference to PendingFrame here.
pattern=r'(?m)^([ \t]*)requests_\.erase\(it\);\n\1/\* Release the internal association'
s,n=re.subn(pattern,lambda m: m[1]+'''const uint64_t ipeToken=frame.ipeToken;const uint32_t ipeSof=frame.ipeSof;
  const bool ipeSuccess=!frame.failed && processedEnabled_ && bool(ipe_);
  requests_.erase(it);
  if(ipeToken)ipa_->frameProcessed(epoch_,ipeSof,ipeToken,ipeSuccess);
  /* Release the internal association''',s);assert n==1,n
p.write_text(s)
patch='';rows=[]
for name in names:
 a=(base/name).read_text() if (base/name).exists() else '';b=(tree/name).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
 rows.append(dict(path=name,sha256=hashlib.sha256((tree/name).read_bytes()).hexdigest()))
(HERE/'0042-camss-ipe-frame-history.patch').write_text(patch)
r=dict(stage=421,source=str(tree),baseline_stage=420,kernel_unchanged=True,private_ipa_version=2,source_hashes=rows,
 owned_actual_statistics_and_sensor_context=True,final_aggregate_receipt_includes_raw_pairing=True,automatic_ipe_numeric_generation=False,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
