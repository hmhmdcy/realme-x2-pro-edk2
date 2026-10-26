from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;volume=storage.mount.mounted_build().parent
old=volume/'libcamera448-capacity-lease';new=storage.candidate()
state=json.loads((HERE.parent/'kernel448/source-state.json').read_text())
assert not new.exists(), 'Do not overwrite an existing candidate'
for row in state['source_hashes']:
 assert hashlib.sha256((old/'src/libcamera-v0.7.2'/row['path']).read_bytes()).hexdigest()==row['sha256']
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
original=(tree/pipeline).read_text()
before=''' while (histogramOrder_.size() > 32) {
  auto old=histograms_.find(histogramOrder_.front());
   if(old!=histograms_.end() && old->second.ipeToken)ipa_->frameProcessed(epoch_,old->first,old->second.ipeToken,false);
   histograms_.erase(histogramOrder_.front()); histogramOrder_.pop_front();
 }
'''
after=''' if (!running_ || epoch != epoch_) return;
 while (histogramOrder_.size() > 32) {
  /* Retire local ownership before a synchronous isolated call can reenter.
   * A nested statistics callback or stop must not resolve this token twice. */
  const uint32_t oldSof=histogramOrder_.front();
  histogramOrder_.pop_front();
  auto old=histograms_.find(oldSof);
  if(old==histograms_.end())continue;
  const uint64_t token=old->second.ipeToken;
  histograms_.erase(old);
  if(token) {
   ipa_->frameProcessed(epoch,oldSof,token,false);
   if (!running_ || epoch != epoch_) return;
  }
 }
'''
assert original.count(before)==1
text=original.replace(before,after);(tree/pipeline).write_text(text)
(HERE/'0061-camss-retire-statistics-before-proxy-call.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+pipeline,tofile='b/'+pipeline)))
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
state.update(stage=450,source=str(tree),baseline_stage=448,source_baseline_stage=448,changed_this_stage=[pipeline],build_pending=True,statistics_retired_before_synchronous_ipa=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=450,only_pipeline_changed=True,source=str(tree),phone_accessed=False,passed=True)))
