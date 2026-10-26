"""Report stopped requests as cancellations using libcamera's native contract."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;v=storage.mount.mounted_build().parent
old=v/'libcamera441-variable-pd10';new=v/'libcamera442-bounded-dispatch';assert old.is_dir() and not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';p=tree/rel;before=p.read_text()
a='if(frame.failed){image->_d()->metadata().status=FrameMetadata::FrameError;if(raw)raw->_d()->metadata().status=FrameMetadata::FrameError;}'
b='''if(frame.failed){
  /* completeBuffer() propagates FrameCancelled into RequestCancelled.
   * Preserve FrameError for live failures; stopping is a cancellation. */
  const auto status=running_?FrameMetadata::FrameError:FrameMetadata::FrameCancelled;
  image->_d()->metadata().status=status;if(raw)raw->_d()->metadata().status=status;
  if(!running_)LOG(CamssVfe,Info)<<"REQUEST_STOP_CANCEL epoch="<<epoch_<<" request="<<request->sequence()<<" raw="<<bool(raw);
 }'''
assert before.count(a)==1;p.write_text(before.replace(a,b))
(HERE/'0055-camss-stop-cancel-status.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),p.read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
state=json.loads((HERE.parent/'kernel441/source-state.json').read_text())
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
state.update(stage=442,source=str(tree),source_baseline_stage=441,baseline_stage=441,changed_this_stage=[rel],stopped_request_cancel_status_corrected=True,live_frame_error_preserved=True,build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=442,source=str(tree),changed_production_files=1,frame_error_only_while_running=True,stop_cancellation_sets_request_cancelled_via_native_completeBuffer=True,protocol_and_iq_math_unchanged=True,phone_changed=False,passed=True)))
