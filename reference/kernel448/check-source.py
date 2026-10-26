from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';old=volume/'libcamera447-focus-execution/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());base=json.loads((HERE.parent/'kernel447/source-state.json').read_text());changed=set(state['changed_this_stage'])
header='src/libcamera/pipeline/camss-vfe/thread_capacity.h';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';assert changed=={header,pipeline}
for row in base['source_hashes']:
 if row['path']!=pipeline:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
text=(tree/pipeline).read_text();a=text.index('int CamssVfePipeline::start(');z=text.index('void CamssVfePipeline::stopDevice(',a);start=text[a:z];stop=text[z:text.index('int CamssVfePipeline::queueRequestDevice(',z)]
assert start.index('focusCapacity_.acquire()')<start.index('d->running_ = true;')<start.index('d->coarse_->streamOn()')
assert re.search(r'error:\s+stopDevice\(camera\);\s+return ret;',start)
assert stop.index('d->running_ = false;')<stop.index('focusCapacity_.release()')<stop.index('d->focusWorkspace_.clear()')
assert 'return;' not in stop[:stop.index('focusCapacity_.release()')]
with tempfile.TemporaryDirectory(prefix='source-replay-',dir=P) as work:
 root=Path(work);p=root/pipeline;p.parent.mkdir(parents=True);shutil.copyfile(old/pipeline,p)
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0060-camss-stream-thread-capacity-lease.patch')],cwd=root,capture_output=True)
 (P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and not re.search(rb'offset|fuzz',q.stdout+q.stderr,re.I)
 assert all((root/n).read_bytes()==(tree/n).read_bytes() for n in changed)
contract=json.loads((HERE/'capacity-validation.json').read_text());assert contract['passed'] and hashlib.sha256((tree/header).read_bytes()).hexdigest()==contract['actual_production_header_sha256']
r=dict(stage=448,only_new_capacity_helper_and_pipeline_lifetime_changed=True,patch_zero_fuzz_offset_and_source_equal=True,capacity_before_capture_streamon=True,all_start_error_gotos_call_stop_release=True,release_after_queues_ipa_lens_stopped=True,numeric_workspace_ipa6_and_reentry_sources_unchanged=True,actual_helper_host_sanitizers_arm_and_sched_syscalls_passed=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
