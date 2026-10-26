"""Expire images by their own arrival age and retain sensor context for late stats."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';p=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';t=p.read_text()
def replace(a,b):
 global t
 assert t.count(a)==1,(a,t.count(a));t=t.replace(a,b)
replace('std::map<uint32_t, FrameBuffer *> images_;','std::map<uint32_t, FrameBuffer *> images_;\n std::map<uint32_t,std::chrono::steady_clock::time_point> imageArrival_;')
replace('d->images_.clear(); d->histograms_.clear();','d->images_.clear(); d->imageArrival_.clear(); d->histograms_.clear();')
replace('images_[sequence] = buffer;','images_[sequence] = buffer;\n imageArrival_[sequence]=std::chrono::steady_clock::now();')
replace('    images_.erase(it);\n\tif (paired)','    images_.erase(it);imageArrival_.erase(sequence);\n\tif (paired)')
replace('\tsensorContexts_.erase(sequence);',' /* Retain the bounded sensor-context history through a late statistics callback. */')
a=t.index(' if(running_ && ipeActive_){deadline_.start');z=t.index('\n std::vector<Request *> pending;',a)
t=t[:a]+''' const auto now=std::chrono::steady_clock::now();
 std::vector<uint32_t> expired;
 for(const auto &[sof,arrival]:imageArrival_)
  if(images_.count(sof) && now-arrival>=std::chrono::milliseconds(250))expired.push_back(sof);
 for(uint32_t sof:expired) {
  if(ipeActive_)break;
  LOG(CamssVfe,Warning)<<"IMAGE_PAIR_TIMEOUT epoch="<<epoch_<<" sof="<<sof;
  finish(sof,histograms_.count(sof),true);
 }
'''+t[z:]
replace('for(Request *request:pending) tryComplete(request,true);','for(Request *request:pending) tryComplete(request,true);\n if(running_ && (!images_.empty() || !requests_.empty()))deadline_.start(std::chrono::milliseconds(250));')
p.write_text(t);s=json.loads((HERE/'source-state.json').read_text())
for r in s['source_hashes']:r['sha256']=hashlib.sha256((tree/r['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
