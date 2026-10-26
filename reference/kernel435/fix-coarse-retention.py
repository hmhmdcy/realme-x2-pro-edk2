"""Retain PD10 owned by a waiting FULL and serialize images in SOF order."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';p=T/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';t=p.read_text()
a=''' while(coarseImages_.size()>stream_.configuration().bufferCount) {
  auto it=coarseImages_.begin();FrameBuffer *old=it->second;coarseImages_.erase(it);
  if(coarse_->queueBuffer(old))LOG(CamssVfe,Error)<<"PD10 stale requeue failed";
 }'''
b=''' while(coarseImages_.size()>stream_.configuration().bufferCount) {
  /* A FULL waiting behind an IPE request already owns its matching PD10.
   * Evict only unclaimed SOFs; reserve buffers continue to drain live IFE. */
  auto it=std::find_if(coarseImages_.begin(),coarseImages_.end(),
                       [this](const auto &entry){return !images_.count(entry.first);});
  if(it==coarseImages_.end())break;
  FrameBuffer *old=it->second;coarseImages_.erase(it);
  if(coarse_->queueBuffer(old))LOG(CamssVfe,Error)<<"PD10 stale requeue failed";
 }'''
assert t.count(a)==1;t=t.replace(a,b)
a='''    if(running_ && ipe_ && processedEnabled_ && ipeActive_) {'''
b='''    /* A later statistics callback must not bypass an older waiting FULL.
     * Both successful numerical history and PD10 retirement follow SOF. */
    if(running_ && ipe_ && processedEnabled_ && sequence!=images_.begin()->first)return;
    if(running_ && ipe_ && processedEnabled_ && ipeActive_) {'''
assert t.count(a)==1;p.write_text(t.replace(a,b))
s=json.loads((HERE/'source-state.json').read_text())
for row in s['source_hashes']:row['sha256']=hashlib.sha256((T/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
