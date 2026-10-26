"""Serialize CAMSS submissions across synchronous IPA event dispatch."""
from pathlib import Path
import difflib,hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent
old=storage.previous.candidate();new=storage.candidate();assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
name='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
p=new/'src/libcamera-v0.7.2'/name;before=p.read_text();s=before
a='\tstd::deque<IspControls> ispControls_;'
assert s.count(a)==1;s=s.replace(a,a+'\n\tbool submittingStatistics_ = false;')
a=''' if (!running_ || !paramsApplied_ || parameterBusy_) return;
 while (!ispControls_.empty()) {'''
b=''' if (!running_ || !paramsApplied_ || parameterBusy_ || !ispHealthy_ || submittingStatistics_) return;
 /* A synchronous isolated IPA call dispatches camera events recursively.
  * Only the outer submission may consume controls or submit statistics.
  * Keep this guard through parameter preparation and processStats(), too.
  */
 submittingStatistics_ = true;
 struct SubmissionGuard {
  bool &active;
  ~SubmissionGuard() { active = false; }
 } submissionGuard{ submittingStatistics_ };
 const uint64_t epoch = epoch_;
 while (!ispControls_.empty()) {'''
assert s.count(a)==1;s=s.replace(a,b)
a='''  auto &request = ispControls_.front();
  ipa::camss::AutoIspUpdate update{};
  int ret = ipa_->applyIspControls(epoch_, uint32_t(std::max<int64_t>(0, int64_t(request.source) + *imageSequenceOffset_)), request.controls, &update);
  if (ret == -EAGAIN) return;'''
b='''  /* Own the entry before calling out: callbacks may append or clear queues. */
  IspControls request = std::move(ispControls_.front());
  ispControls_.pop_front();
  ipa::camss::AutoIspUpdate update{};
  int ret = ipa_->applyIspControls(epoch, uint32_t(std::max<int64_t>(0, int64_t(request.source) + *imageSequenceOffset_)), request.controls, &update);
  if (!running_ || epoch_ != epoch) return;
  if (ret == -EAGAIN) {
   ispControls_.push_front(std::move(request));
   return;
  }'''
assert s.count(a)==1;s=s.replace(a,b)
a='''  ispControls_.pop_front();
  if (update.valid) { queueIspUpdate(update); return; }'''
b='''  if (update.valid) { queueIspUpdate(update); return; }
  if (parameterBusy_ || !ispHealthy_) return;'''
assert s.count(a)==1;s=s.replace(a,b)
a='''  if (parameterBusy_) return;
  (void)sequence;'''
b='''  if (!running_ || epoch_ != epoch || parameterBusy_ || !ispHealthy_) return;
  (void)sequence;'''
assert s.count(a)==1;s=s.replace(a,b)
p.write_text(s)
(HERE/'camss-submit-reentrancy.patch').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True),s.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)))
(HERE/'camss-vfe-after.cpp').write_text(s)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=362,baseline_stage=361,source=str(new/'src/libcamera-v0.7.2'),file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),isolated_ipc_preserved=True,queue_entry_owned_before_ipc=True,installed=False),indent=2)+'\n')
print('Prepared CAMSS serialized submission candidate; dispatcher361 retained.')
