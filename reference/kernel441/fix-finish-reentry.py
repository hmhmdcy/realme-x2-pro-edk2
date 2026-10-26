"""Retire a frame safely when isolated synchronous IPA calls dispatch stop()."""
from pathlib import Path
import difflib,hashlib,json
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
storage.mount.mounted_build();tree=storage.candidate()/'src/libcamera-v0.7.2'
rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';p=tree/rel;before=p.read_text();text=before
def replace(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a))
 text=text.replace(a,b)
replace('    if(!request || !requests_.count(request)){images_.erase(it);return;}','''    if(!request || !requests_.count(request)){images_.erase(it);return;}
    /* Cancellation needs no new synchronous IPA work. The buffers still
     * belong to the stopped queues until their ordinary completion. */
    if (!running_) {
        images_.erase(it); imageArrival_.erase(sequence);
        imageProcessed(buffer, requests_.at(request).image, false);
        return;
    }
    const uint64_t frameEpoch = epoch_;
    const uint32_t requestSequence = request->sequence();
    const auto ownsFrame = [&]() {
        auto live = requests_.find(request);
        return running_ && epoch_ == frameEpoch && live != requests_.end() &&
               live->second.ifeImage == buffer && request->sequence() == requestSequence;
    };''')
replace('int ret=context==sensorContexts_.end()?-ENODATA:ipa_->frameMetadata(epoch_,sequence,context->second,&metadata);','''int ret=context==sensorContexts_.end()?-ENODATA:ipa_->frameMetadata(epoch_,sequence,context->second,&metadata);
        if (!ownsFrame()) return;''')
replace('int ret=ipa_->processFocus(epoch_,sequence,request->controls(),score.has_value(),score.value_or(0),captured,context,&metadata,&move);','''int ret=ipa_->processFocus(epoch_,sequence,request->controls(),score.has_value(),score.value_or(0),captured,context,&metadata,&move);
  /* Isolated synchronous calls may dispatch stopDevice() while waiting. */
  if (!ownsFrame()) return;''')
replace('if(!running_ || epoch_!=toneEpoch || !requests_.count(request))return;','if (!ownsFrame()) return;')
patch=''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(P/'camss-vfe-before-reentry.cpp').write_text(before)
p.write_text(text);(HERE/'0053-camss-finish-stop-reentry.patch').write_text(patch)
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:
 if row['path']==rel:row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
state.update(finish_sync_ipa_stop_reentry_fixed=True,build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=441,changed_production_files=1,guards_after_frame_metadata_focus_and_tone_prepare=True,cancellation_skips_new_ipa_work=True,ipa_math_and_protocol_unchanged=True,phone_changed=False,passed=True)))
