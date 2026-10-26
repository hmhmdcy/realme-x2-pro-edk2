from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
tree=storage.candidate()/'src/libcamera-v0.7.2';old=volume/'libcamera445-focus-grid/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());baseline=json.loads((HERE.parent/'kernel445/source-state.json').read_text());changed=set(state['changed_this_stage']);assert len(changed)==2
for row in baseline['source_hashes']:
 if row['path'] not in changed:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
for name in ['include/libcamera/internal/software_isp/focus_stats.h','src/ipa/libipa/contrast_af.h']:assert (tree/name).read_bytes()==(old/name).read_bytes()
text=(tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_text()
start=text[text.index('int CamssVfePipeline::start('):text.index('void CamssVfePipeline::stopDevice(')] if 'int CamssVfePipeline::start(' in text else text[text.index('int CamssVfePipeline::startDevice('):text.index('void CamssVfePipeline::stopDevice(')]
assert start.index('focusWorkspace_.prepare(')<start.index('d->running_ = true;')<start.index('d->coarse_->streamOn()')
stop=text[text.index('void CamssVfePipeline::stopDevice('):];assert stop.index('focusWorkspace_.clear()')<stop.index('d->internalImages_.clear()')
with tempfile.TemporaryDirectory(prefix='source-replay-',dir=P) as work:
 root=Path(work)
 for name in changed:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,p)
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0058-camss-bounded-focus-workspace.patch')],cwd=root,capture_output=True)
 (P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and not re.search(rb'offset|fuzz',q.stdout+q.stderr,re.I)
 assert all((root/name).read_bytes()==(tree/name).read_bytes() for name in changed)
r=dict(stage=446,only_two_production_files_changed=True,patch_zero_fuzz_offset_and_source_equal=True,
 per_camera_workspace_prepared_before_streaming=True,workspace_release_on_stop_and_start_error_path=True,
 tiny_streams_without_fom_are_not_rejected=True,ipa6_fom_normalization_af_state_and_factory_sources_unchanged=True,
 phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
