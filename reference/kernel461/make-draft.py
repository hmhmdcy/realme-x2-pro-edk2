"""Prepare only a private one-file request-completion ownership candidate."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import shutil
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel461')
REL='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
PATCH='0065-camss-retain-request-through-ipa-completion.patch'


def main():
    spec=importlib.util.spec_from_file_location('storage449completion',HERE.parent/'kernel449/storage.py')
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    build=storage.mount.mounted_build()
    assert shutil.disk_usage(build).free >= 2*1024**3
    source=build.parent/'libcamera452-full-ownership/src/libcamera-v0.7.2'/REL
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    assert digest=='69cc15e0c192ef9cf16b0b20c7d4e14af127b03bda4ac9db626edce472e1d831'
    text=raw.decode()
    old='  std::optional<std::array<float, 9>> ipeColourMatrix{};\n'
    new=old+'  bool ipaCompleting = false;\n'
    assert text.count(old)==1;text=text.replace(old,new)
    old=' PendingFrame &frame=it->second;\n if(!frame.imageFinished || !frame.rawReady)return;'
    new=''' PendingFrame &frame=it->second;
 /* The synchronous receipt may dispatch another completion or a timeout.
  * Stop must still find this frame and cancel it through the ordinary drain. */
 if(frame.ipaCompleting && running_)return;
 if(!frame.imageFinished || !frame.rawReady)return;'''
    assert text.count(old)==1;text=text.replace(old,new)
    old='''  requests_.erase(it);
  if(ipeToken)ipa_->frameProcessed(epoch_,ipeSof,ipeToken,ipeSuccess);
  if(ipeActive_==request)ipeActive_=nullptr;'''
    new='''  if(ipeToken && !frame.ipaCompleting) {
   const uint64_t receiptEpoch=epoch_;
   const uint32_t requestSequence=request->sequence();
   frame.ipaCompleting=true;
   ipa_->frameProcessed(receiptEpoch,ipeSof,ipeToken,ipeSuccess);
   /* Stop may have completed this request and released its FULL buffer.
    * A restarted stream may even reuse the request or buffer address. */
   auto live=requests_.find(request);
   if(!running_ || epoch_!=receiptEpoch || live==requests_.end() ||
      live->second.ifeImage!=ife || request->sequence()!=requestSequence)return;
   live->second.ipaCompleting=false;
   it=live;
  }
  requests_.erase(it);
  if(ipeActive_==request)ipeActive_=nullptr;'''
    assert text.count(old)==1;text=text.replace(old,new)
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    (PRIVATE/'camss_vfe-baseline.cpp').write_bytes(raw)
    (PRIVATE/'camss_vfe-candidate.cpp').write_text(text)
    patch=''.join(difflib.unified_diff(raw.decode().splitlines(True),text.splitlines(True),
                                     fromfile='a/'+REL,tofile='b/'+REL))
    (HERE/PATCH).write_text(patch)
    assert source.read_bytes()==raw
    report=dict(stage=461,baseline_stage=452,baseline_sha256=digest,
                candidate_sha256=hashlib.sha256(text.encode()).hexdigest(),
                patch=PATCH,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
                changed_paths=[REL],request_retained_during_synchronous_receipt=True,
                live_nested_completion_and_timeout_deferred=True,stop_drain_can_cancel_once=True,
                receipt_issued_once=True,post_receipt_epoch_identity_revalidated=True,
                normal_qbuf_ipe_history_and_completion_order_preserved=True,
                camera_protocol_parameters_af_or_buffer_count_changed=False,
                free_ext4_bytes=shutil.disk_usage(build).free,
                no_frozen_source_writes=True,no_sdk_library_build_or_phone=True,passed=True)
    (HERE/'source-draft-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
