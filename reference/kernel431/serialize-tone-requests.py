"""Let final numerical receipts precede the next single-pending IPA calculation."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';p=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';t=p.read_text()
def replace(a,b):
 global t
 assert t.count(a)==1,(a,t.count(a));t=t.replace(a,b)
replace('std::map<Request *, PendingFrame> requests_;','std::map<Request *, PendingFrame> requests_;\n Request *ipeActive_ = nullptr;')
replace('d->requests_.clear();d->internalRequests_.clear();','d->requests_.clear();d->ipeActive_=nullptr;d->internalRequests_.clear();')
replace('    if(coarseEnabled_ && running_ && buffer->metadata().status==FrameMetadata::FrameSuccess) {','''    if(running_ && ipe_ && processedEnabled_ && ipeActive_) {
        if(!deadline_.isRunning())deadline_.start(std::chrono::milliseconds(250));
        return;
    }
    if(coarseEnabled_ && running_ && buffer->metadata().status==FrameMetadata::FrameSuccess) {''')
replace('    images_.erase(it);\n\tif (paired)', '    if(running_ && ipe_ && processedEnabled_)ipeActive_=request;\n    images_.erase(it);\n\tif (paired)')
replace('if(ipeToken)ipa_->frameProcessed(epoch_,ipeSof,ipeToken,ipeSuccess);','if(ipeToken)ipa_->frameProcessed(epoch_,ipeSof,ipeToken,ipeSuccess);\n  if(ipeActive_==request)ipeActive_=nullptr;')
replace('handler()->completeRequest(request);\n if(images_.empty()', '''handler()->completeRequest(request);
 if(running_ && !ipeActive_ && !images_.empty()) {
  const uint32_t next=images_.begin()->first;
  if(histograms_.count(next))finish(next,true);
  else completeMissingStatistics();
 }
 if(images_.empty()''')
replace(' while (!images_.empty()) finish(images_.begin()->first,histograms_.count(images_.begin()->first),true);',' if(running_ && ipeActive_){deadline_.start(std::chrono::milliseconds(250));return;}\n while (!images_.empty()) finish(images_.begin()->first,histograms_.count(images_.begin()->first),true);')
p.write_text(t);s=json.loads((HERE/'source-state.json').read_text())
for r in s['source_hashes']:r['sha256']=hashlib.sha256((tree/r['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
