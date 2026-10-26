"""Reduce the common focus/tone IPC pair without changing either algorithm."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;v=storage.mount.mounted_build().parent
old=v/'libcamera442-bounded-dispatch';new=storage.candidate();assert old.is_dir()
if new.exists():
 assert not (HERE/'source-state.json').exists()
 baseline=json.loads((HERE.parent/'kernel442/source-state.json').read_text())
 assert all(hashlib.sha256((new/'src/libcamera-v0.7.2'/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in baseline['source_hashes'])
else:shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';original={};changed=[]
def edit(name,a,b):
 p=tree/name;text=p.read_text();original.setdefault(name,text)
 a=a.lstrip(' \t');b=b.lstrip(' \t')
 assert text.count(a)==1,(name,a,text.count(a));p.write_text(text.replace(a,b))
 if name not in changed:changed.append(name)
mojom='include/libcamera/ipa/camss.mojom';ipa='src/ipa/camss-vfe/camss.cpp';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
edit(mojom,'  [async] lensPositionApplied', '''  prepareFocusedIpe(uint64 epoch, uint32 sof, uint64 token, libcamera.ControlList controls,
                    bool valid, int32 score, uint64 capturedMonotonic, SensorContext sensorContext)
                    => (int32 focusStatus, libcamera.ControlList metadata, LensMove move,
                        bool tonePrepared, int32 toneStatus, array<uint8> parameters,
                        uint64 revision, bool fresh);
  [async] lensPositionApplied''')
declaration=''' int prepareFocusedIpe(uint64_t epoch,uint32_t sof,uint64_t token,const ControlList &controls,
                       bool valid,int32_t score,uint64_t captured,const SensorContext &sensorContext,
                       ControlList *metadata,LensMove *move,bool *tonePrepared,int32_t *toneStatus,
                       std::vector<uint8_t> *parameters,uint64_t *revision,bool *fresh) override;
'''
edit(ipa,' void lensPositionApplied(uint64_t epoch,uint32_t serial,int32_t status,uint64_t monotonic) override;',declaration+' void lensPositionApplied(uint64_t epoch,uint32_t serial,int32_t status,uint64_t monotonic) override;')
implementation='''int IPACamss::prepareFocusedIpe(uint64_t epoch,uint32_t sof,uint64_t token,const ControlList &controls,
                               bool valid,int32_t score,uint64_t captured,const SensorContext &sensorContext,
                               ControlList *metadata,LensMove *move,bool *tonePrepared,int32_t *toneStatus,
                               std::vector<uint8_t> *parameters,uint64_t *revision,bool *fresh)
{
 std::lock_guard<std::recursive_mutex> stateLock(stateMutex_);
 if (!metadata || !move || !tonePrepared || !toneStatus || !parameters || !revision || !fresh)
  return -EINVAL;
 *tonePrepared=false;*toneStatus=0;parameters->clear();*revision=0;*fresh=false;
 const int focusStatus=processFocus(epoch,sof,controls,valid,score,captured,sensorContext,metadata,move);
 /* A lens move must retain the host's command/ACK before tone preparation.
  * No algorithm or final-receipt history is bypassed by the common case. */
 if (!move->valid) {
  *tonePrepared=true;
  *toneStatus=prepareIpeParameters(epoch,sof,token,parameters,revision,fresh);
 }
 return focusStatus;
}

'''
edit(ipa,'void IPACamss::lensPositionApplied(',implementation+'void IPACamss::lensPositionApplied(')
edit(ipa,'IPA_MODULE_API_VERSION, 5, "camss-vfe", "camss-vfe",','IPA_MODULE_API_VERSION, 6, "camss-vfe", "camss-vfe",')
edit(pipeline,'createIPA<ipa::camss::IPAProxyCamss>(5, 5)','createIPA<ipa::camss::IPAProxyCamss>(6, 6)')
edit(pipeline,'  if (lensActive_ && running_) {','''  std::vector<uint8_t> focusedTone;
  uint64_t focusedRevision=0;bool focusedFresh=false,focusedPrepared=false;int32_t focusedToneStatus=0;
  if (lensActive_ && running_) {''')
edit(pipeline,'  const auto score=measureFrameFocus(buffer,focusConfig);','''  const auto focusBegin=std::chrono::steady_clock::now();
  const auto score=measureFrameFocus(buffer,focusConfig);
  const auto focusMeasured=std::chrono::steady_clock::now();''')
edit(pipeline,'  int ret=ipa_->processFocus(epoch_,sequence,request->controls(),score.has_value(),score.value_or(0),captured,context,&metadata,&move);','''  const bool combined=ipe_ && processedEnabled_ && buffer->metadata().status==FrameMetadata::FrameSuccess;
  int ret;
  if (combined)
   ret=ipa_->prepareFocusedIpe(epoch_,sequence,requests_.at(request).ipeToken,request->controls(),
                             score.has_value(),score.value_or(0),captured,context,&metadata,&move,
                             &focusedPrepared,&focusedToneStatus,&focusedTone,&focusedRevision,&focusedFresh);
  else
   ret=ipa_->processFocus(epoch_,sequence,request->controls(),score.has_value(),score.value_or(0),captured,context,&metadata,&move);
  const auto focusDispatched=std::chrono::steady_clock::now();
  LOG(CamssVfe,Debug)<<"FRAME_IPA_PREPARE epoch="<<frameEpoch<<" sof="<<sequence<<" combined="<<combined
   <<" focus-us="<<std::chrono::duration_cast<std::chrono::microseconds>(focusMeasured-focusBegin).count()
   <<" dispatch-us="<<std::chrono::duration_cast<std::chrono::microseconds>(focusDispatched-focusMeasured).count()
   <<" focus-status="<<ret<<" tone-prepared="<<focusedPrepared;''')
edit(pipeline,'  int ret=ipa_->prepareIpeParameters(toneEpoch,sequence,toneToken,&tone,&toneRevision,&toneFresh);','''  const auto toneBegin=std::chrono::steady_clock::now();
  int ret;
  if (focusedPrepared) {
   ret=focusedToneStatus;tone=std::move(focusedTone);toneRevision=focusedRevision;toneFresh=focusedFresh;
  } else ret=ipa_->prepareIpeParameters(toneEpoch,sequence,toneToken,&tone,&toneRevision,&toneFresh);
  LOG(CamssVfe,Debug)<<"TONE_IPA_PREPARE epoch="<<toneEpoch<<" sof="<<sequence<<" cached="<<focusedPrepared
   <<" dispatch-us="<<std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-toneBegin).count()
   <<" status="<<ret;''')
patch=''.join(''.join(difflib.unified_diff(original[n].splitlines(True),(tree/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in changed)
(HERE/'0056-camss-focused-ipe-dispatch.patch').write_text(patch)
state=json.loads((HERE.parent/'kernel442/source-state.json').read_text())
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
state.update(stage=444,source=str(tree),baseline_stage=442,source_baseline_stage=442,changed_this_stage=changed,
 private_ipa_version=6,common_focus_tone_rpc_pair_combined=True,lens_move_retains_separate_ack_before_tone=True,build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=444,source=str(tree),changed_production_files=len(changed),private_ipa_version=6,existing_focus_and_tone_functions_unchanged=True,phone_changed=False,passed=True)))
